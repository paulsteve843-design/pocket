"""
Scene segmentation engine - splits audio drama into logical cinematic scenes
Uses acoustic features, speaker changes, and content analysis
"""
import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import numpy as np

@dataclass
class Scene:
    scene_id: str
    start_time: float
    end_time: float
    duration: float
    speakers: List[str]
    dialogue: List[Dict]
    location_hint: str
    mood: str
    acoustic_events: List[str]
    ambiguity_flags: List[str]
    suggested_shots: int = 3

    def to_dict(self):
        return asdict(self)

class SceneSegmenter:
    def __init__(self, config):
        self.config = config
        self.min_duration = config.pipeline.min_scene_duration
        self.max_duration = config.pipeline.max_scene_duration
        self.silence_threshold = config.pipeline.silence_threshold

        # Location inference patterns
        self.location_patterns = {
            "interior_residential": [
                r"\b(room|house|apartment|kitchen|bedroom|bathroom|living room|door|creak|floor|wall|ceiling|window|curtain|sofa|couch|table|chair)\b",
                r"\b(home|inside|indoor|upstairs|downstairs|hallway|corridor|closet|basement|attic)\b"
            ],
            "exterior_urban": [
                r"\b(street|road|sidewalk|alley|avenue|boulevard|intersection|traffic|car|taxi|bus|subway|metro|city|downtown|building|skyscraper)\b",
                r"\b(rain|wet|puddle|neon|streetlight|lamp post|sidewalk|pedestrian|crowd|urban)\b"
            ],
            "interior_vehicle": [
                r"\b(car|truck|van|jeep|engine|dashboard|steering wheel|seatbelt|rearview|windshield|drive|driving)\b",
                r"\b(vehicle|automobile|motor|honk|traffic jam|highway|freeway|road trip)\b"
            ],
            "interior_office": [
                r"\b(office|desk|computer|monitor|keyboard|meeting|conference|boss|colleague|employee|corporate|company)\b",
                r"\b(cubicle|boardroom|presentation|report|deadline|project|client|business)\b"
            ],
            "exterior_nature": [
                r"\b(forest|woods|tree|mountain|river|lake|ocean|beach|field|meadow|valley|hill|cliff|desert)\b",
                r"\b(wind|breeze|storm|thunder|lightning|snow|fog|mist|sunset|sunrise|dawn|dusk|wildlife)\b"
            ],
            "interior_public": [
                r"\b(restaurant|cafe|bar|pub|club|theater|cinema|mall|store|shop|library|museum|hospital|clinic)\b",
                r"\b(waiter|menu|order|bill|receipt|stage|audience|crowd|public|service)\b"
            ]
        }

        # Mood inference patterns
        self.mood_indicators = {
            "tense": r"\b(wait|stop|don't|never|can't|won't|afraid|scared|nervous|anxious|danger|threat|gun|knife|blood|run|hide)\b",
            "romantic": r"\b(love|kiss|always|together|beautiful|heart|miss|want|need|hold|touch|close|intimate|passion)\b",
            "suspense": r"\b(secret|know|truth|hiding|follow|watching|listen|hear|someone|there|behind|dark|shadow|footstep)\b",
            "action": r"\b(run|hurry|now|go|move|fast|quick|chase|fight|punch|kick|jump|crash|bang|explosion|fire)\b",
            "melancholy": r"\b(remember|past|gone|lost|alone|empty|sad|cry|tears|regret|sorry|forgive|never again)\b",
            "mysterious": r"\b(what|who|where|why|how|strange|weird|odd|unclear|unknown|disappear|vanish|clue|puzzle)\b"
        }

        # Scene boundary markers
        self.boundary_markers = [
            r"\b(later|meanwhile|the next day|hours later|days later|weeks later|months later|years later)\b",
            r"\b(somewhere else|elsewhere|in another place|across town|back at)\b",
            r"\b(flashback|memory|recall|remember when)\b",
            r"\b(same time|simultaneously|at the same time)\b",
            r"\b(scene\s+\d+|act\s+\d+|chapter\s+\d+)\b"
        ]

    def detect_boundaries(self, segments: List[Dict]) -> List[int]:
        """Find scene boundary indices based on multiple cues"""
        boundaries = [0]
        scores = np.zeros(len(segments))

        for i in range(1, len(segments)):
            prev = segments[i-1]
            curr = segments[i]

            score = 0.0

            # Long silence gap
            gap = curr["start"] - prev["end"]
            if gap > self.silence_threshold * 2:
                score += 0.4 * min(gap / self.silence_threshold, 2.0)

            # Speaker change after sustained dialogue
            if prev["speaker"] != curr["speaker"]:
                if i > 1 and segments[i-2]["speaker"] == prev["speaker"]:
                    score += 0.3

            # Explicit scene markers in text
            text_lower = curr["text"].lower()
            for pattern in self.boundary_markers:
                if re.search(pattern, text_lower):
                    score += 0.5

            # Location shift keywords
            prev_text = " ".join([s["text"] for s in segments[max(0,i-3):i]]).lower()
            curr_text = " ".join([s["text"] for s in segments[i:min(i+3, len(segments))]]).lower()

            prev_loc = self._detect_location(prev_text)
            curr_loc = self._detect_location(curr_text)
            if prev_loc != curr_loc and prev_loc != "unknown" and curr_loc != "unknown":
                score += 0.3

            # Time shift indicators
            if any(marker in text_lower for marker in ["morning", "afternoon", "evening", "night", "dawn", "dusk"]):
                if not any(marker in prev_text for marker in ["morning", "afternoon", "evening", "night", "dawn", "dusk"]):
                    score += 0.2

            scores[i] = score

        # Dynamic threshold based on score distribution
        threshold = np.percentile(scores[scores > 0], 60) if np.any(scores > 0) else 0.5

        for i, score in enumerate(scores):
            if score >= threshold:
                # Ensure minimum scene duration
                if boundaries:
                    last_boundary = boundaries[-1]
                    if segments[i]["start"] - segments[last_boundary]["start"] >= self.min_duration:
                        boundaries.append(i)

        boundaries.append(len(segments))
        return boundaries

    def _detect_location(self, text: str) -> str:
        """Infer location from text content"""
        text_lower = text.lower()
        scores = {}

        for loc, patterns in self.location_patterns.items():
            score = sum(len(re.findall(p, text_lower)) for p in patterns)
            scores[loc] = score

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "unknown"

    def _detect_mood(self, segments: List[Dict]) -> str:
        """Infer dominant mood from dialogue"""
        combined_text = " ".join([s["text"] for s in segments]).lower()
        scores = {}

        for mood, pattern in self.mood_indicators.items():
            scores[mood] = len(re.findall(pattern, combined_text))

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "neutral"

    def _extract_ambiguity(self, segments: List[Dict]) -> List[str]:
        """Flag narrative ambiguities that need director interpretation"""
        flags = []
        combined = " ".join([s["text"] for s in segments]).lower()

        # Off-screen actions
        if re.search(r"\b(sound of|heard|noise|crash|bang|scream from|voice from)\b", combined):
            flags.append("off_screen_action")

        # Internal monologue / voiceover
        if re.search(r"\b(thought|remember|wondered|realized|knew|felt)\b", combined):
            flags.append("internal_monologue")

        # Unseen presence
        if re.search(r"\b(someone|something|presence|feeling watched|not alone)\b", combined):
            flags.append("unseen_presence")

        # Time ambiguity
        if re.search(r"\b(sometime|eventually|sooner or later|one day|someday)\b", combined):
            flags.append("time_ambiguity")

        return flags

    def process(self, transcript_path: Path) -> List[Scene]:
        """Main entry: transcript -> list of Scene objects"""
        with open(transcript_path) as f:
            data = json.load(f)

        segments = data.get("segments", [])
        if not segments:
            return []

        boundaries = self.detect_boundaries(segments)
        scenes = []

        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1]
            scene_segs = segments[start_idx:end_idx]

            duration = scene_segs[-1]["end"] - scene_segs[0]["start"]

            # Skip if too short
            if duration < self.min_duration:
                continue

            # Split if too long
            if duration > self.max_duration:
                mid = len(scene_segs) // 2
                scene_segs = scene_segs[:mid]
                duration = scene_segs[-1]["end"] - scene_segs[0]["start"]

            speakers = list(set(s["speaker"] for s in scene_segs if s.get("speaker")))

            dialogue = [
                {
                    "speaker": s["speaker"],
                    "text": s["text"],
                    "start": s["start"],
                    "end": s["end"],
                    "confidence": s.get("confidence", 1.0)
                }
                for s in scene_segs
            ]

            # Estimate shot count based on dialogue density
            dialogue_density = len(dialogue) / max(duration, 1)
            suggested_shots = min(
                max(int(dialogue_density * 2) + 1, 2),
                self.config.pipeline.max_shots_per_scene
            )

            scene = Scene(
                scene_id=f"{transcript_path.stem}_sc{len(scenes):04d}",
                start_time=scene_segs[0]["start"],
                end_time=scene_segs[-1]["end"],
                duration=duration,
                speakers=speakers,
                dialogue=dialogue,
                location_hint=self._detect_location(" ".join([s["text"] for s in scene_segs])),
                mood=self._detect_mood(scene_segs),
                acoustic_events=[],  # Populated by audio analysis module
                ambiguity_flags=self._extract_ambiguity(scene_segs),
                suggested_shots=suggested_shots
            )
            scenes.append(scene)

        return scenes

    def save_scenes(self, scenes: List[Scene], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump([s.to_dict() for s in scenes], f, indent=2)
        print(f"[SceneSegmenter] Saved {len(scenes)} scenes to {output_path}")
