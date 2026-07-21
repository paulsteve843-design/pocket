#!/usr/bin/env python3
"""Stage 7: Final assembly and color grading"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import ConfigManager
from core.post_processor import PostProcessor
from core.path_resolver import episode_path

def main():
    config = ConfigManager("config/system.yaml")
    processor = PostProcessor(config)

    # Collect all final clips in order
    lipsync_dir = episode_path("output/lipsync", "output/lipsync")
    final_clips = sorted(lipsync_dir.glob("*_final.mp4"))

    if not final_clips:
        print(f"ERROR: No processed clips found in {lipsync_dir}/")
        return

    print(f"\n{'='*60}")
    print(f"ASSEMBLING FINAL MOVIE")
    print(f"{'='*60}")
    print(f"Clips to assemble: {len(final_clips)}")

    # Find original audio
    input_dir = episode_path(".", "assets/input")
    audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3")) +                   list(input_dir.glob("*.flac")) + list(input_dir.glob("*.m4a"))

    if not audio_files:
        print(f"ERROR: No audio source found in {input_dir}/")
        return

    # Assemble
    output_path = episode_path("output/final_movie.mp4", "output/final_movie.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processor.assemble_final(final_clips, audio_files[0], output_path)

    # Apply color grade
    graded_path = episode_path("output/final_movie_graded.mp4", "output/final_movie_graded.mp4")
    processor.apply_color_grade(output_path, graded_path, grade_type="neutral")

    print(f"\n{'='*60}")
    print("PRODUCTION COMPLETE")
    print(f"{'='*60}")
    print(f"\nFinal outputs:")
    print(f"  Ungraded: {output_path.absolute()}")
    print(f"  Graded:   {graded_path.absolute()}")
    print(f"\nAll intermediate files preserved in output/")

if __name__ == "__main__":
    main()
