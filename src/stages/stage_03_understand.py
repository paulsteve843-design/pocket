#!/usr/bin/env python3
"""Stage 3: Story understanding and cinematic translation via LLM"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import ConfigManager
from core.story_engine import StoryEngine
from core.path_resolver import episode_path, drama_path

def main():
    config = ConfigManager("config/system.yaml")
    engine = StoryEngine(config)

    # Load registries. When running under the web studio these live at the
    # drama level (dramas/<id>/characters.json etc.) so they're shared
    # across all episodes of that drama; otherwise fall back to assets/.
    char_path = drama_path("characters.json", "assets/characters.json")
    loc_path = drama_path("locations.json", "assets/locations.json")
    prop_path = drama_path("props.json", "assets/props.json")

    missing = []
    if not char_path.exists():
        missing.append(str(char_path))
    if not loc_path.exists():
        missing.append(str(loc_path))

    if missing:
        print("=" * 60)
        print("MISSING DEFINITION FILES:")
        print("=" * 60)
        for f in missing:
            print(f"  - {f}")
        print("\nCreate these files before running this stage.")
        print("See SETUP_GUIDE.md for format examples.")
        return

    engine.load_character_registry(char_path)
    engine.load_location_registry(loc_path)
    if prop_path.exists():
        engine.load_prop_registry(prop_path)

    scenes_dir = episode_path("output/scenes", "output/scenes")
    output_dir = episode_path("output/prompts", "output/prompts")
    output_dir.mkdir(parents=True, exist_ok=True)

    for scene_file in scenes_dir.glob("*_scenes.json"):
        print(f"\n{'='*60}")
        print(f"PROCESSING STORY: {scene_file.name}")
        print(f"{'='*60}")
        engine.process_all_scenes(scene_file, output_dir)

    print(f"\n{'='*60}")
    print("STAGE 3 COMPLETE")
    print(f"{'='*60}")
    print("\nReview generated prompts in output/prompts/")
    print("Then run: python run_pipeline.py 4")

if __name__ == "__main__":
    main()
