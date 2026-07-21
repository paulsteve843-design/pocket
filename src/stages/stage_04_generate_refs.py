#!/usr/bin/env python3
"""Stage 4: Generate reference images for characters and locations"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import ConfigManager
from core.reference_generator import ReferenceGenerator
from core.path_resolver import drama_path

def main():
    config = ConfigManager("config/system.yaml")
    generator = ReferenceGenerator(config)

    output_dir = drama_path("refs", "assets/refs")

    char_path = drama_path("characters.json", "assets/characters.json")
    loc_path = drama_path("locations.json", "assets/locations.json")

    if not char_path.exists():
        print(f"ERROR: {char_path} not found")
        return

    refs = generator.generate_all_references(char_path, loc_path, output_dir)
    generator.unload_model()

    print(f"\n{'='*60}")
    print(f"GENERATED {len(refs)} REFERENCE IMAGES")
    print(f"{'='*60}")
    for key, path in refs.items():
        print(f"  {key:30s} -> {path}")

    print(f"\n{'─'*60}")
    print("REVIEW these images. If any character looks wrong:")
    print("  1. Edit assets/characters.json with better descriptions")
    print("  2. Delete the bad reference image")
    print("  3. Rerun this stage")
    print(f"{'─'*60}")
    print("\nThen run: python run_pipeline.py 5")

if __name__ == "__main__":
    main()
