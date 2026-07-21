#!/usr/bin/env python3
"""Stage 2: Scene segmentation from transcript"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import ConfigManager
from core.scene_segmenter import SceneSegmenter
from core.path_resolver import episode_path

def main():
    config = ConfigManager("config/system.yaml")
    segmenter = SceneSegmenter(config)

    transcript_dir = episode_path("output/transcripts", "output/transcripts")
    output_dir = episode_path("output/scenes", "output/scenes")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not list(transcript_dir.glob("*.json")):
        print("No transcripts found. Run Stage 1 first.")
        return

    for transcript_file in transcript_dir.glob("*.json"):
        print(f"\n{'='*60}")
        print(f"SEGMENTING: {transcript_file.name}")
        print(f"{'='*60}")

        scenes = segmenter.process(transcript_file)
        output_path = output_dir / f"{transcript_file.stem}_scenes.json"
        segmenter.save_scenes(scenes, output_path)

        print(f"\n{'─'*60}")
        print(f"DETECTED {len(scenes)} SCENES:")
        print(f"{'─'*60}")
        for s in scenes:
            print(f"  {s.scene_id:20s} | {s.duration:5.1f}s | {s.location_hint:20s} | {s.mood:12s} | {len(s.dialogue):2d} lines")

        print(f"\n{'─'*60}")
        print("AMBIGUITY FLAGS (require your interpretation):")
        print(f"{'─'*60}")
        for s in scenes:
            if s.ambiguity_flags:
                print(f"  {s.scene_id}: {', '.join(s.ambiguity_flags)}")

    print(f"\n{'='*60}")
    print("STAGE 2 COMPLETE")
    print(f"{'='*60}")
    print("\nCreate your character and location definitions:")
    print("  - assets/characters.json")
    print("  - assets/locations.json")
    print("\nThen run: python run_pipeline.py 3")

if __name__ == "__main__":
    main()
