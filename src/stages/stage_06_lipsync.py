#!/usr/bin/env python3
"""Stage 6: Lip synchronization and video enhancement"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import ConfigManager
from core.post_processor import PostProcessor
from core.path_resolver import episode_path

def main():
    config = ConfigManager("config/system.yaml")
    processor = PostProcessor(config)

    prompts_dir = episode_path("output/prompts", "output/prompts")
    clips_dir = episode_path("output/clips", "output/clips")
    output_dir = episode_path("output/lipsync", "output/lipsync")

    # Find original audio. Under the web studio this is the episode's own
    # uploaded audio file; standalone CLI usage falls back to assets/input/.
    input_dir = episode_path(".", "assets/input")
    audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3")) +                   list(input_dir.glob("*.flac")) + list(input_dir.glob("*.m4a"))

    if not audio_files:
        print(f"ERROR: No audio source found in {input_dir}/")
        return

    audio_source = audio_files[0]

    processed_count = 0
    for prompt_file in prompts_dir.glob("*.json"):
        with open(prompt_file) as f:
            scene_data = json.load(f)

        print(f"\n{'='*60}")
        print(f"PROCESSING: {scene_data['scene_id']}")
        print(f"{'='*60}")

        processed = processor.process_scene_clips(
            scene_data,
            audio_source,
            clips_dir,
            output_dir
        )
        processed_count += len(processed)
        print(f"  -> {len(processed)} clips processed")

    print(f"\n{'='*60}")
    print("STAGE 6 COMPLETE")
    print(f"{'='*60}")
    print(f"Total clips processed: {processed_count}")
    print("\nThen run: python run_pipeline.py 7")

if __name__ == "__main__":
    main()
