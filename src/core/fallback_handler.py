"""
Fallback Handler - generates blue placeholder frames when generation fails
Ensures pipeline continuity regardless of content sensitivity
"""
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from diffusers import DiffusionPipeline
import cv2

class FallbackHandler:
    def __init__(self, config):
        self.config = config
        self.max_retries = config.pipeline.fallback.max_retries
        self.fallback_color = config.pipeline.fallback.fallback_frame_color
        self.fallback_duration = config.pipeline.fallback.fallback_frame_duration
        self.fallback_prompt = config.pipeline.fallback.fallback_prompt
        self.narrator_skip = config.pipeline.fallback.narrator_skip_visual

        self._retry_counts = {}
        self._blue_frame_cache = {}

    def should_skip_character(self, speaker_role: str) -> bool:
        """Check if this speaker should skip visual generation (narrator, etc.)"""
        narrator_keywords = ["narrator", "voiceover", "announcer", "commentary", 
                            "storyteller", "guide", "host"]
        return any(kw in speaker_role.lower() for kw in narrator_keywords) and self.narrator_skip

    def get_retry_count(self, shot_id: str) -> int:
        return self._retry_counts.get(shot_id, 0)

    def increment_retry(self, shot_id: str):
        self._retry_counts[shot_id] = self._retry_counts.get(shot_id, 0) + 1

    def should_fallback(self, shot_id: str) -> bool:
        return self.get_retry_count(shot_id) >= self.max_retries

    def generate_blue_frame(self, width: int, height: int, duration: float, 
                            fps: int = 25, output_path: Path = None) -> Path:
        """Generate a cinematic blue placeholder video"""

        cache_key = f"{width}x{height}_{duration}s"
        if cache_key in self._blue_frame_cache:
            cached = self._blue_frame_cache[cache_key]
            if output_path:
                import shutil
                shutil.copy(cached, output_path)
                return output_path
            return cached

        # Create blue frame with subtle variation (not flat)
        num_frames = int(duration * fps)

        # Base blue color with slight gradient
        r, g, b = self.fallback_color

        frames = []
        for i in range(num_frames):
            # Subtle animated gradient
            factor = (i / num_frames) * 0.1  # 10% variation
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # Create gradient from top-left to bottom-right
            for y in range(height):
                for x in range(width):
                    grad = (x / width + y / height) / 2
                    frame[y, x] = [
                        int(r * (0.95 + grad * 0.1)),
                        int(g * (0.95 + grad * 0.1)),
                        int(b * (0.95 + grad * 0.1))
                    ]

            frames.append(frame)

        # Write video
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

            for frame in frames:
                writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

            writer.release()

            # Cache
            self._blue_frame_cache[cache_key] = output_path
            return output_path

        return frames

    def generate_fallback_with_text(self, width: int, height: int, 
                                    text: str, duration: float,
                                    output_path: Path) -> Path:
        """Generate blue frame with scene description text overlay"""

        num_frames = int(duration * 25)
        r, g, b = self.fallback_color

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(output_path), fourcc, 25, (width, height))

        for i in range(num_frames):
            # Blue background
            frame = np.full((height, width, 3), [r, g, b], dtype=np.uint8)

            # Add text overlay
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(text, font, 0.7, 2)[0]
            text_x = (width - text_size[0]) // 2
            text_y = height // 2

            # White text with shadow
            cv2.putText(frame, text, (text_x + 2, text_y + 2), font, 0.7, (0, 0, 0), 2)
            cv2.putText(frame, text, (text_x, text_y), font, 0.7, (255, 255, 255), 2)

            writer.write(frame)

        writer.release()
        return output_path

    def handle_generation_failure(self, shot_spec: dict, error: Exception,
                                   output_path: Path) -> Path:
        """Main entry: called when video generation fails"""

        shot_id = shot_spec.get("shot_number", "unknown")
        self.increment_retry(shot_id)

        print(f"[FallbackHandler] Generation failed for shot {shot_id} (attempt {self.get_retry_count(shot_id)}/{self.max_retries})")

        if self.should_fallback(shot_id):
            print(f"[FallbackHandler] Max retries reached. Generating blue placeholder.")

            # Get dimensions from shot spec
            shot_type = shot_spec.get("type", "medium_shot")
            width, height = 512, 320  # default

            if "close" in shot_type or "insert" in shot_type:
                width, height = 384, 512
            elif "wide" in shot_type or "establishing" in shot_type:
                width, height = 704, 384

            duration = shot_spec.get("duration_estimate", self.fallback_duration)

            # Generate with descriptive text
            scene_desc = shot_spec.get("type", "scene") + " - " + shot_spec.get("subject", "unknown")
            return self.generate_fallback_with_text(width, height, scene_desc, duration, output_path)

        # Re-raise to allow retry
        raise error
