#!/usr/bin/env python3
"""
Audio Drama Cinema Studio - Web Backend
Actually runs the real pipeline (src/stages/*) per drama/episode in the
background, tracks real progress, and serves real generated assets.
"""

import os
import sys
import json
import uuid
import threading
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Project paths
BASE_DIR = Path(__file__).parent
DRAMAS_DIR = BASE_DIR / "dramas"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"
RUN_PIPELINE_SCRIPT = BASE_DIR / "run_pipeline.py"

DRAMAS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

STAGE_NAMES = [
    "Speech Recognition & Diarization",
    "Scene Segmentation",
    "Story Understanding (LLM)",
    "Reference Image Generation",
    "Video Clip Generation",
    "Lip Sync & Enhancement",
    "Final Assembly",
]

# ---------------------------------------------------------------------------
# In-memory job tracking for background pipeline runs.
# Keyed by job_id. Each entry tracks the actual subprocess so status polling
# reflects reality instead of an assumed "started" state.
# ---------------------------------------------------------------------------
JOBS = {}
JOBS_LOCK = threading.Lock()


def safe_drama_dir(drama_id: str) -> Path:
    """Resolve a drama_id to a directory strictly inside DRAMAS_DIR, guarding
    against path traversal via a crafted drama_id."""
    candidate = (DRAMAS_DIR / drama_id).resolve()
    if DRAMAS_DIR.resolve() not in candidate.parents and candidate != DRAMAS_DIR.resolve():
        raise ValueError("Invalid drama_id")
    return candidate


def episode_dir_for(drama_dir: Path, episode: str) -> Path:
    return drama_dir / "episodes" / f"ep_{int(episode):03d}"


def load_metadata(drama_dir: Path) -> dict:
    meta_file = drama_dir / "metadata.json"
    with open(meta_file) as f:
        meta = json.load(f)
    # Backfill keys that may be missing from dramas created by an older
    # server version, or edited by hand, so the rest of the code can rely
    # on these always being present.
    meta.setdefault("episodes", [])
    meta.setdefault("characters", {})
    meta.setdefault("locations", {})
    meta.setdefault("title", "Untitled")
    meta.setdefault("language", "auto")
    meta.setdefault("theme", "auto")
    return meta


def save_metadata(drama_dir: Path, meta: dict):
    with open(drama_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)


def sync_registry_file(drama_dir: Path, kind: str, meta: dict):
    """Write dramas/<id>/characters.json or locations.json from the metadata
    so the real pipeline stages (which read these files directly) always see
    what's actually stored, without a separate "commit" step."""
    registry_path = drama_dir / f"{kind}.json"
    with open(registry_path, "w") as f:
        json.dump(meta.get(kind, {}), f, indent=2)


def run_pipeline_job(job_id: str, drama_dir: Path, episode_dir: Path, stages=None):
    """Runs in a background thread. Launches the real pipeline as a
    subprocess (so heavy model loading doesn't block the HTTP server) and
    streams its output to a log file that the status endpoint tails.

    If `stages` is given (e.g. [1, 2] for Analyze Audio), only those stages
    run, in order, each as its own subprocess invocation; otherwise the full
    1-7 pipeline runs via `run_pipeline.py all`.
    """
    log_path = episode_dir / "pipeline.log"
    episode_dir.mkdir(parents=True, exist_ok=True)

    with JOBS_LOCK:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["log_path"] = str(log_path)

    try:
        with open(log_path, "w") as log_file:
            if stages:
                returncode = 0
                for stage_num in stages:
                    cmd = [sys.executable, str(RUN_PIPELINE_SCRIPT), str(stage_num),
                           "--drama-dir", str(drama_dir), "--episode-dir", str(episode_dir)]
                    process = subprocess.Popen(
                        cmd, stdout=log_file, stderr=subprocess.STDOUT, cwd=str(BASE_DIR)
                    )
                    with JOBS_LOCK:
                        JOBS[job_id]["pid"] = process.pid
                    returncode = process.wait()
                    log_file.flush()
                    if returncode != 0:
                        break
            else:
                cmd = [sys.executable, str(RUN_PIPELINE_SCRIPT), "all",
                       "--drama-dir", str(drama_dir), "--episode-dir", str(episode_dir)]
                process = subprocess.Popen(
                    cmd, stdout=log_file, stderr=subprocess.STDOUT, cwd=str(BASE_DIR)
                )
                with JOBS_LOCK:
                    JOBS[job_id]["pid"] = process.pid
                returncode = process.wait()

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "complete" if returncode == 0 else "failed"
            JOBS[job_id]["returncode"] = returncode
            JOBS[job_id]["finished_at"] = datetime.now().isoformat()
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
            JOBS[job_id]["finished_at"] = datetime.now().isoformat()


def parse_job_progress(log_path: Path):
    """Best-effort progress read from the pipeline's own log output, so the
    UI can show a real stage name and percentage instead of a fake timer."""
    current_stage = 0
    last_lines = []
    if log_path.exists():
        try:
            text = log_path.read_text(errors="replace")
            for name_idx, name in enumerate(STAGE_NAMES, start=1):
                if f"STAGE {name_idx}:" in text:
                    current_stage = name_idx
            last_lines = text.strip().splitlines()[-15:]
        except Exception:
            pass
    total = len(STAGE_NAMES)
    pct = int((current_stage / total) * 100) if current_stage else 0
    stage_name = STAGE_NAMES[current_stage - 1] if current_stage else "Starting..."
    return {
        "current_stage": current_stage,
        "total_stages": total,
        "stage_name": stage_name,
        "percent": pct,
        "log_tail": last_lines,
    }


def parse_multipart(headers, rfile):
    """Parse multipart/form-data without cgi module."""
    content_type = headers.get('Content-Type', '')
    if not content_type.startswith('multipart/form-data'):
        return None

    boundary = None
    for part in content_type.split(';'):
        part = part.strip()
        if part.startswith('boundary='):
            boundary = part[9:].strip('"')
            break

    if not boundary:
        return None

    content_length = int(headers.get('Content-Length', 0))
    data = rfile.read(content_length)

    boundary_bytes = ("--" + boundary).encode()
    parts = {}

    segments = data.split(boundary_bytes)
    for segment in segments:
        segment = segment.strip()
        if not segment or segment == b'--':
            continue

        header_end = segment.find(b'\r\n\r\n')
        if header_end == -1:
            header_end = segment.find(b'\n\n')
            if header_end == -1:
                continue
            header_data = segment[:header_end].decode('utf-8', errors='replace')
            body = segment[header_end + 2:]
        else:
            header_data = segment[:header_end].decode('utf-8', errors='replace')
            body = segment[header_end + 4:]

        if body.endswith(b'\r\n'):
            body = body[:-2]
        if body.endswith(b'\n'):
            body = body[:-1]

        name = None
        filename = None
        for line in header_data.split('\r\n'):
            if line.startswith('Content-Disposition'):
                for item in line.split(';'):
                    item = item.strip()
                    if item.startswith('name='):
                        name = item[5:].strip('"\'')
                    elif item.startswith('filename='):
                        filename = item[9:].strip('"\'')

        if name:
            if filename:
                parts[name] = {"filename": filename, "data": body}
            else:
                parts[name] = body.decode('utf-8', errors='replace')

    return parts


class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json_safe(self, data, status=200):
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            response = json.dumps(data).encode('utf-8')
            self.wfile.write(response)
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)

            if path == '/' or path == '/index.html':
                self.serve_file('studio_ui.html', 'text/html')
            elif path == '/api/dramas':
                self.handle_get_dramas()
            elif path.startswith('/api/dramas/'):
                parts = path.split('/')
                if len(parts) >= 4:
                    drama_id = parts[3]
                    self.handle_get_drama(drama_id)
                else:
                    self.send_error(404)
            elif path == '/api/characters':
                self.handle_get_characters(query)
            elif path == '/api/locations':
                self.handle_get_locations(query)
            elif path == '/api/pipeline/status':
                self.handle_pipeline_status(query)
            elif path == '/api/analyze/speakers':
                self.handle_get_speakers(query)
            elif path == '/api/results':
                self.handle_get_results(query)
            elif path == '/api/video':
                self.handle_get_video(query)
            elif path == '/api/image':
                self.handle_get_image(query)
            elif path == '/api/status':
                self.handle_status()
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Error in do_GET: {e}")
            traceback.print_exc()
            self.send_json_safe({"error": str(e)}, 500)

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------
    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path == '/api/dramas':
                self.handle_create_drama()
            elif path == '/api/episodes':
                self.handle_upload_episode()
            elif path == '/api/characters':
                self.handle_add_character()
            elif path == '/api/locations':
                self.handle_add_location()
            elif path == '/api/references':
                self.handle_upload_reference()
            elif path == '/api/pipeline':
                self.handle_run_pipeline()
            elif path == '/api/analyze':
                self.handle_run_analyze()
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Error in do_POST: {e}")
            traceback.print_exc()
            self.send_json_safe({"error": str(e)}, 500)

    def serve_file(self, filename, content_type):
        filepath = BASE_DIR / filename
        if filepath.exists():
            try:
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            except (ConnectionAbortedError, BrokenPipeError, OSError):
                pass
        else:
            self.send_error(404)

    # ------------------------------------------------------------------
    # Dramas
    # ------------------------------------------------------------------
    def handle_get_dramas(self):
        dramas = []
        for drama_dir in sorted(DRAMAS_DIR.glob("drama_*")):
            meta_file = drama_dir / "metadata.json"
            if meta_file.exists():
                try:
                    with open(meta_file) as f:
                        meta = json.load(f)
                    episodes_dir = drama_dir / "episodes"
                    episode_count = len(list(episodes_dir.glob("ep_*"))) if episodes_dir.exists() else 0
                    dramas.append({
                        "id": drama_dir.name,
                        "title": meta.get("title", "Untitled"),
                        "language": meta.get("language", "auto"),
                        "theme": meta.get("theme", "auto"),
                        "episodes": episode_count,
                        "created": meta.get("created", "")
                    })
                except Exception as e:
                    print(f"Error reading drama {drama_dir}: {e}")

        self.send_json_safe(dramas)

    def handle_get_drama(self, drama_id):
        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return
        meta_file = drama_dir / "metadata.json"
        if meta_file.exists():
            with open(meta_file) as f:
                meta = json.load(f)
            self.send_json_safe(meta)
        else:
            self.send_json_safe({"error": "Drama not found"}, 404)

    def handle_create_drama(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        drama_id = f"drama_{uuid.uuid4().hex[:8]}"
        drama_dir = DRAMAS_DIR / drama_id
        drama_dir.mkdir(exist_ok=True)

        metadata = {
            "id": drama_id,
            "title": data.get("title", "Untitled"),
            "language": data.get("language", "auto"),
            "theme": data.get("theme", "auto"),
            "created": datetime.now().isoformat(),
            "episodes": [],
            "characters": {},
            "locations": {}
        }

        save_metadata(drama_dir, metadata)
        sync_registry_file(drama_dir, "characters", metadata)
        sync_registry_file(drama_dir, "locations", metadata)

        (drama_dir / "episodes").mkdir(exist_ok=True)
        (drama_dir / "refs").mkdir(exist_ok=True)

        self.send_json_safe({"id": drama_id, **metadata})

    # ------------------------------------------------------------------
    # Episodes / audio upload
    # ------------------------------------------------------------------
    def handle_upload_episode(self):
        parts = parse_multipart(self.headers, self.rfile)

        if not parts:
            self.send_json_safe({"error": "Could not parse multipart data"}, 400)
            return

        drama_id = parts.get('drama_id', '')
        episode_num = parts.get('episode', '1')

        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return

        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return
        if not drama_dir.exists():
            self.send_json_safe({"error": "Drama not found"}, 404)
            return

        audio_field = parts.get('audio')
        if audio_field and isinstance(audio_field, dict) and audio_field.get('filename'):
            ep_dir = episode_dir_for(drama_dir, episode_num)
            ep_dir.mkdir(parents=True, exist_ok=True)

            # Remove any previous audio for this episode so the pipeline
            # always sees exactly one, current file -- this is what makes
            # re-uploading a new audio file actually change the output,
            # instead of stale files silently accumulating.
            for old in list(ep_dir.glob("audio.*")):
                old.unlink()

            ext = Path(audio_field['filename']).suffix
            audio_path = ep_dir / f"audio{ext}"

            with open(audio_path, 'wb') as f:
                f.write(audio_field['data'])

            meta = load_metadata(drama_dir)

            ep_str = str(int(episode_num))
            if ep_str not in meta["episodes"]:
                meta["episodes"].append(ep_str)

            save_metadata(drama_dir, meta)

            self.send_json_safe({
                "success": True,
                "drama_id": drama_id,
                "episode": episode_num,
                "file": str(audio_path),
                "size": audio_path.stat().st_size
            })
            return

        self.send_json_safe({"error": "No audio file provided"}, 400)

    # ------------------------------------------------------------------
    # Characters
    # ------------------------------------------------------------------
    def handle_get_characters(self, query):
        drama_id = query.get('drama_id', [''])[0]
        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return
        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return
        meta = load_metadata(drama_dir)
        self.send_json_safe(meta.get("characters", {}))

    def handle_add_character(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        drama_id = data.get('drama_id', '')
        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return

        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return

        meta = load_metadata(drama_dir)

        char_name = data.get('name', '').upper()
        meta["characters"][char_name] = {
            "role": data.get('role', 'supporting'),
            "age": data.get('age', ''),
            "gender": data.get('gender', ''),
            "appearance": data.get('appearance', ''),
            "clothing": data.get('clothing', ''),
            "expression": data.get('expression', ''),
            "added": datetime.now().isoformat()
        }

        save_metadata(drama_dir, meta)
        sync_registry_file(drama_dir, "characters", meta)

        self.send_json_safe({"success": True, "character": char_name})

    # ------------------------------------------------------------------
    # Locations (previously had no server-side handler at all -- the UI's
    # "Add Location" button had nothing real to call)
    # ------------------------------------------------------------------
    def handle_get_locations(self, query):
        drama_id = query.get('drama_id', [''])[0]
        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return
        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return
        meta = load_metadata(drama_dir)
        self.send_json_safe(meta.get("locations", {}))

    def handle_add_location(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        drama_id = data.get('drama_id', '')
        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return

        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return

        meta = load_metadata(drama_dir)
        if "locations" not in meta:
            meta["locations"] = {}

        loc_name = data.get('name', '')
        meta["locations"][loc_name] = {
            "description": data.get('description', ''),
            "scene_type": data.get('scene_type', 'interior'),
            "lighting": data.get('lighting', 'neutral'),
            "time_of_day": data.get('time_of_day', 'day'),
            "atmosphere": data.get('atmosphere', ''),
            "added": datetime.now().isoformat()
        }

        save_metadata(drama_dir, meta)
        sync_registry_file(drama_dir, "locations", meta)

        self.send_json_safe({"success": True, "location": loc_name})

    # ------------------------------------------------------------------
    # Reference image upload (makes the UI's "Upload Ref" button real --
    # it's read by ReferenceGenerator.generate_all_references, which skips
    # FLUX generation for any character/location that has one)
    # ------------------------------------------------------------------
    def handle_upload_reference(self):
        parts = parse_multipart(self.headers, self.rfile)
        if not parts:
            self.send_json_safe({"error": "Could not parse multipart data"}, 400)
            return

        drama_id = parts.get('drama_id', '')
        asset_type = parts.get('type', '')  # 'character' or 'location'
        name = parts.get('name', '')

        if not (drama_id and asset_type and name):
            self.send_json_safe({"error": "Missing drama_id, type, or name"}, 400)
            return

        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return

        image_field = parts.get('image')
        if not (image_field and isinstance(image_field, dict) and image_field.get('filename')):
            self.send_json_safe({"error": "No image file provided"}, 400)
            return

        uploads_dir = drama_dir / "refs" / "user_uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(image_field['filename']).suffix or ".png"
        dest = uploads_dir / f"{asset_type}_{name.lower().replace(' ', '_')}{ext}"
        with open(dest, 'wb') as f:
            f.write(image_field['data'])

        meta = load_metadata(drama_dir)
        kind = "characters" if asset_type == "character" else "locations"
        key = name.upper() if kind == "characters" else name
        if key in meta.get(kind, {}):
            meta[kind][key]["reference_image"] = str(dest)
            save_metadata(drama_dir, meta)
            sync_registry_file(drama_dir, kind, meta)

        self.send_json_safe({"success": True, "path": str(dest)})

    # ------------------------------------------------------------------
    # Pipeline execution -- this used to be a stub that faked "started".
    # It now actually launches run_pipeline.py in the background, scoped
    # to the chosen drama/episode, and returns a real job_id to poll.
    # ------------------------------------------------------------------
    def handle_run_analyze(self):
        """Runs transcription + scene segmentation only (stages 1-2), so the
        UI can show real detected speakers before committing to the full,
        much slower, video-generation pipeline."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        drama_id = data.get('drama_id', '')
        episode = data.get('episode', '1')

        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return
        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return
        if not drama_dir.exists():
            self.send_json_safe({"error": "Drama not found"}, 404)
            return

        ep_dir = episode_dir_for(drama_dir, episode)
        if not list(ep_dir.glob("audio.*")):
            self.send_json_safe(
                {"error": f"No audio uploaded for episode {episode}. Upload audio first."}, 400)
            return

        job_id = uuid.uuid4().hex[:12]
        with JOBS_LOCK:
            JOBS[job_id] = {
                "job_id": job_id,
                "kind": "analyze",
                "drama_id": drama_id,
                "episode": episode,
                "status": "starting",
                "started_at": datetime.now().isoformat(),
            }

        thread = threading.Thread(
            target=run_pipeline_job,
            args=(job_id, drama_dir, ep_dir, [1, 2]),
            daemon=True
        )
        thread.start()

        self.send_json_safe({"success": True, "job_id": job_id, "status": "starting"})

    def handle_get_speakers(self, query):
        """Reads the real transcript produced by stage 1 and returns actual
        detected speakers with real line/word counts -- this is what feeds
        the 'detected characters' list in the UI, replacing the old
        hardcoded MARGARET/COUNT_VORONIN demo data."""
        drama_id = query.get('drama_id', [''])[0]
        episode = query.get('episode', ['1'])[0]
        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return
        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return

        ep_dir = episode_dir_for(drama_dir, episode)
        transcript_dir = ep_dir / "output" / "transcripts"
        transcripts = list(transcript_dir.glob("*.json")) if transcript_dir.exists() else []

        if not transcripts:
            self.send_json_safe({"ready": False, "speakers": []})
            return

        with open(transcripts[0]) as f:
            transcript = json.load(f)

        summary = transcript.get("speaker_summary", {})
        speakers = [
            {
                "name": name,
                "segments": info.get("segments", 0),
                "words": info.get("words", 0),
                "duration": round(info.get("duration", 0), 1),
            }
            for name, info in summary.items()
        ]
        speakers.sort(key=lambda s: -s["words"])

        # Also surface detected scene/location count if segmentation ran
        scenes_dir = ep_dir / "output" / "scenes"
        scene_files = list(scenes_dir.glob("*_scenes.json")) if scenes_dir.exists() else []
        scene_count = 0
        location_hints = []
        if scene_files:
            with open(scene_files[0]) as f:
                scene_data = json.load(f)
            scenes_list = scene_data if isinstance(scene_data, list) else scene_data.get("scenes", [])
            scene_count = len(scenes_list)
            seen = set()
            for s in scenes_list:
                hint = s.get("location_hint")
                if hint and hint not in seen:
                    seen.add(hint)
                    location_hints.append(hint)

        self.send_json_safe({
            "ready": True,
            "speakers": speakers,
            "scene_count": scene_count,
            "location_hints": location_hints,
        })

    def handle_run_pipeline(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        drama_id = data.get('drama_id', '')
        episode = data.get('episode', '1')

        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return

        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return
        if not drama_dir.exists():
            self.send_json_safe({"error": "Drama not found"}, 404)
            return

        ep_dir = episode_dir_for(drama_dir, episode)
        audio_files = list(ep_dir.glob("audio.*"))
        if not audio_files:
            self.send_json_safe(
                {"error": f"No audio uploaded for episode {episode}. Upload audio first."}, 400)
            return

        job_id = uuid.uuid4().hex[:12]
        with JOBS_LOCK:
            JOBS[job_id] = {
                "job_id": job_id,
                "drama_id": drama_id,
                "episode": episode,
                "status": "starting",
                "started_at": datetime.now().isoformat(),
            }

        thread = threading.Thread(
            target=run_pipeline_job,
            args=(job_id, drama_dir, ep_dir, None),
            daemon=True
        )
        thread.start()

        self.send_json_safe({
            "success": True,
            "job_id": job_id,
            "drama_id": drama_id,
            "episode": episode,
            "status": "starting"
        })

    def handle_pipeline_status(self, query):
        job_id = query.get('job_id', [''])[0]
        with JOBS_LOCK:
            job = JOBS.get(job_id)
        if not job:
            self.send_json_safe({"error": "Unknown job_id"}, 404)
            return

        result = dict(job)
        log_path = job.get("log_path")
        if log_path:
            result["progress"] = parse_job_progress(Path(log_path))
        self.send_json_safe(result)

    # ------------------------------------------------------------------
    # Results -- reads what's actually on disk instead of returning
    # hardcoded demo content
    # ------------------------------------------------------------------
    def handle_get_results(self, query):
        drama_id = query.get('drama_id', [''])[0]
        episode = query.get('episode', ['1'])[0]
        if not drama_id:
            self.send_json_safe({"error": "Missing drama_id"}, 400)
            return
        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_json_safe({"error": "Invalid drama_id"}, 400)
            return

        ep_dir = episode_dir_for(drama_dir, episode)
        out = ep_dir / "output"

        def list_files(sub):
            d = out / sub
            return [str(p.relative_to(BASE_DIR)) for p in sorted(d.glob("*"))] if d.exists() else []

        final_video = out / "final_movie_graded.mp4"
        if not final_video.exists():
            final_video = out / "final_movie.mp4"

        result = {
            "drama_id": drama_id,
            "episode": episode,
            "final_video": str(final_video.relative_to(BASE_DIR)) if final_video.exists() else None,
            "transcripts": list_files("transcripts"),
            "scenes": list_files("scenes"),
            "prompts": list_files("prompts"),
            "clips": list_files("clips"),
            "lipsync": list_files("lipsync"),
            "characters": load_metadata(drama_dir).get("characters", {}),
            "locations": load_metadata(drama_dir).get("locations", {}),
            "refs": [str(p.relative_to(BASE_DIR)) for p in sorted((drama_dir / "refs").glob("*.png"))] if (drama_dir / "refs").exists() else [],
        }
        self.send_json_safe(result)

    def handle_get_video(self, query):
        drama_id = query.get('drama_id', [''])[0]
        episode = query.get('episode', ['1'])[0]
        try:
            drama_dir = safe_drama_dir(drama_id)
        except ValueError:
            self.send_error(400)
            return
        ep_dir = episode_dir_for(drama_dir, episode)
        out = ep_dir / "output"
        video_path = out / "final_movie_graded.mp4"
        if not video_path.exists():
            video_path = out / "final_movie.mp4"
        if not video_path.exists():
            self.send_error(404)
            return
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(video_path, 'rb') as f:
                self.wfile.write(f.read())
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def handle_get_image(self, query):
        """Serves reference images. `path` must be a file inside DRAMAS_DIR
        (guarded against path traversal)."""
        rel_path = query.get('path', [''])[0]
        if not rel_path:
            self.send_error(400)
            return
        full_path = (BASE_DIR / rel_path).resolve()
        if DRAMAS_DIR.resolve() not in full_path.parents or not full_path.exists():
            self.send_error(404)
            return
        content_type = 'image/png' if full_path.suffix == '.png' else 'image/jpeg'
        try:
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(full_path, 'rb') as f:
                self.wfile.write(f.read())
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def handle_status(self):
        status = {
            "dramas_dir": str(DRAMAS_DIR),
            "assets_dir": str(ASSETS_DIR),
            "active_jobs": sum(1 for j in JOBS.values() if j.get("status") in ("starting", "running")),
        }
        try:
            import torch
            status["pytorch"] = torch.__version__
            status["cuda"] = torch.cuda.is_available()
            status["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        except Exception as e:
            status["pytorch"] = None
            status["cuda"] = False
            status["gpu_check_error"] = str(e)
        self.send_json_safe(status)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def run_server(port=8080):
    server = HTTPServer(('localhost', port), APIHandler)
    print("="*60)
    print("AUDIO DRAMA CINEMA STUDIO")
    print("="*60)
    print(f"Server running at: http://localhost:{port}")
    print("Open this URL in your browser")
    print("Press Ctrl+C to stop")
    print("="*60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        port = int(sys.argv[2])
    run_server(port)





'''dev'''