"""
Post-Processing Engine - lip sync, enhancement, upscaling, frame interpolation
Uses FFmpeg, Real-ESRGAN, RIFE, and optional Wav2Lip
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
import shutil

class PostProcessor:
    def __init__(self, config):
        self.config = config
        self.ffmpeg_path = self._resolve_ffmpeg()
        self.ffprobe_path = shutil.which("ffprobe") or "ffprobe"

    @staticmethod
    def _resolve_ffmpeg() -> str:
        """Find a usable ffmpeg binary. Prefers a system install (needed for
        ffprobe anyway), but falls back to the portable binary bundled with
        imageio-ffmpeg (already a project dependency) so this works out of
        the box on Windows, where ffmpeg isn't installed by default."""
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    def extract_audio_segment(self, audio_path: Path, start: float, 
                              end: float, output: Path) -> Path:
        """Extract a specific audio segment for lip sync"""
        duration = end - start
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(audio_path),
            "-ss", str(start),
            "-t", str(duration),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output

    def lip_sync(self, video_path: Path, audio_path: Path, 
                 output_path: Path) -> Path:
        """
        Apply lip synchronization using Wav2Lip
        Falls back to audio overlay if Wav2Lip not available
        """
        wav2lip_dir = Path("models/wav2lip")

        if not (wav2lip_dir / "inference.py").exists():
            print(f"[PostProcessor] Wav2Lip not found, using audio overlay")
            return self._audio_overlay(video_path, audio_path, output_path)

        checkpoint = wav2lip_dir / "wav2lip_gan.pth"
        if not checkpoint.exists():
            print(f"[PostProcessor] Wav2Lip checkpoint missing, using audio overlay")
            return self._audio_overlay(video_path, audio_path, output_path)

        cmd = [
            "python", str(wav2lip_dir / "inference.py"),
            "--checkpoint_path", str(checkpoint),
            "--face", str(video_path),
            "--audio", str(audio_path),
            "--outfile", str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError:
            print(f"[PostProcessor] Wav2Lip failed, using audio overlay")
            return self._audio_overlay(video_path, audio_path, output_path)

    def _audio_overlay(self, video_path: Path, audio_path: Path, 
                       output_path: Path) -> Path:
        """Simple audio overlay when lip sync unavailable"""
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def upscale_video(self, input_path: Path, output_path: Path, 
                      scale: int = 2) -> Path:
        """Upscale video using Real-ESRGAN or FFmpeg lanczos fallback"""
        realesrgan_path = Path(f"models/{self.config.models.upscaler_model}")

        if realesrgan_path.exists():
            # Use Real-ESRGAN
            cmd = [
                "python", "-m", "realesrgan",
                "-i", str(input_path),
                "-o", str(output_path),
                "-n", self.config.models.upscaler_model.replace(".pth", ""),
                "-s", str(scale)
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return output_path
            except subprocess.CalledProcessError:
                pass

        # Fallback: FFmpeg lanczos
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(input_path),
            "-vf", f"scale=iw*{scale}:ih*{scale}:flags=lanczos",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "copy",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def interpolate_frames(self, input_path: Path, output_path: Path,
                           target_fps: int = 60) -> Path:
        """Frame interpolation using RIFE or FFmpeg minterpolate"""
        # Try RIFE first
        rife_dir = Path("models/rife")
        if (rife_dir / "inference_video.py").exists():
            try:
                cmd = [
                    "python", str(rife_dir / "inference_video.py"),
                    "--video", str(input_path),
                    "--output", str(output_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                return output_path
            except subprocess.CalledProcessError:
                pass

        # Fallback: FFmpeg motion interpolation
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(input_path),
            "-vf", f"minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:fps={target_fps}'",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "copy",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def apply_color_grade(self, input_path: Path, output_path: Path,
                          grade_type: str = "neutral") -> Path:
        """Apply color grading LUT"""
        lut_params = {
            "neutral": "",
            "warm": "colorbalance=rs=.1:gs=.05:bs=-.05,eq=saturation=1.1",
            "cool": "colorbalance=rs=-.05:gs=.02:bs=.1,eq=saturation=.9",
            "high_contrast": "eq=contrast=1.3:brightness=-.05",
            "desaturated": "eq=saturation=.6:contrast=1.1",
            "noir": "eq=contrast=1.5:brightness=-.1:saturation=.2"
        }

        vf = lut_params.get(grade_type, "")
        if not vf:
            shutil.copy(input_path, output_path)
            return output_path

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(input_path),
            "-vf", vf,
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "copy",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def assemble_final(self, clip_paths: List[Path], audio_path: Path,
                       output_path: Path, transitions: str = "hard") -> Path:
        """Assemble final movie from clips with original audio"""

        # Create concat list
        concat_file = Path("temp_concat.txt")
        with open(concat_file, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.absolute()}'\n")

        # Concatenate video clips
        temp_video = Path("temp_assembled.mp4")
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(temp_video)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Mix with original audio
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(temp_video),
            "-i", str(audio_path),
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "aac", "-b:a", "320k",
            "-shortest",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Cleanup
        temp_video.unlink(missing_ok=True)
        concat_file.unlink(missing_ok=True)

        return output_path

    def process_scene_clips(self, scene_data: Dict, audio_source: Path,
                            input_dir: Path, output_dir: Path) -> List[Path]:
        """Process all clips for a single scene"""
        output_dir.mkdir(parents=True, exist_ok=True)
        processed = []

        scene_id = scene_data["scene_id"]
        dialogue = scene_data.get("dialogue", [])

        # Find all clips for this scene
        clips = sorted(input_dir.glob(f"{scene_id}_s*.mp4"))

        for idx, clip_path in enumerate(clips):
            base_name = f"{scene_id}_s{idx:03d}"

            # Step 1: Lip sync (if dialogue exists)
            if idx < len(dialogue):
                seg = dialogue[idx]
                audio_seg = output_dir / f"{base_name}_audio.wav"
                self.extract_audio_segment(audio_source, seg["start"], seg["end"], audio_seg)

                synced = output_dir / f"{base_name}_synced.mp4"
                self.lip_sync(clip_path, audio_seg, synced)
                current = synced
            else:
                current = clip_path

            # Step 2: Upscale
            upscaled = output_dir / f"{base_name}_upscaled.mp4"
            self.upscale_video(current, upscaled)

            # Step 3: Frame interpolation
            interpolated = output_dir / f"{base_name}_final.mp4"
            self.interpolate_frames(upscaled, interpolated)

            processed.append(interpolated)

        return processed
