#!/usr/bin/env python3
"""Stage 5: Generate video clips from cinematic specifications"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import ConfigManager
from core.video_generator import VideoGenerator
from core.fallback_handler import FallbackHandler
from core.path_resolver import episode_path, drama_path

def main():
    config = ConfigManager("config/system.yaml")
    generator = VideoGenerator(config)
    fallback = FallbackHandler(config)
    generator.set_fallback_handler(fallback)

    prompts_dir = episode_path("output/prompts", "output/prompts")
    output_dir = episode_path("output/clips", "output/clips")
    refs_dir = drama_path("refs", "assets/refs")

    # Build character reference mapping
    character_refs = {}
    for ref in refs_dir.glob("character_*.png"):
        name = ref.stem.replace("character_", "")
        character_refs[name.upper()] = ref

    # Load character definitions to identify narrators
    narrator_speakers = []
    char_path = drama_path("characters.json", "assets/characters.json")
    if char_path.exists():
        with open(char_path) as f:
            chars = json.load(f)
        for name, data in chars.items():
            if data.get("role", "").lower() in ["narrator", "voiceover", "announcer"]:
                narrator_speakers.append(name.upper())

    total_shots = 0
    fallback_count = 0

    for prompt_file in sorted(prompts_dir.glob("*.json")):
        print(f"\n{'='*60}")
        print(f"GENERATING VIDEO: {prompt_file.stem}")
        print(f"{'='*60}")

        generated = generator.process_scene_file(
            prompt_file,
            character_refs,
            output_dir,
            narrator_speakers=narrator_speakers
        )

        total_shots += len(generated)
        fallback_count += sum(1 for g in generated if g.get("is_fallback", False))

        print(f"\n  Generated: {len(generated)} shots")
        if fallback_count > 0:
            print(f"  Fallbacks (blue frames): {fallback_count}")

    generator.unload_model()

    print(f"\n{'='*60}")
    print("STAGE 5 COMPLETE")
    print(f"{'='*60}")
    print(f"Total shots: {total_shots}")
    if fallback_count > 0:
        print(f"Blue frame fallbacks: {fallback_count} (audio continues uninterrupted)")
    print("\nThen run: python run_pipeline.py 6")

if __name__ == "__main__":
    main()
