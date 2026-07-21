#!/usr/bin/env python3
"""
Audio Drama to Cinema - Master Pipeline Runner
Usage: python run_pipeline.py [stage_number_or_name]
       python run_pipeline.py all  # Run full pipeline

       # Scoped to a specific drama/episode (used by studio_server.py, but
       # you can also use this yourself to keep multiple projects separate):
       python run_pipeline.py all --drama-dir dramas/drama_abc123 --episode-dir dramas/drama_abc123/episodes/ep_001
"""
import sys
import os
import argparse
import subprocess
from pathlib import Path

STAGES = {
    1: ("stage_01_transcribe.py", "Speech Recognition & Diarization"),
    2: ("stage_02_segment.py", "Scene Segmentation"),
    3: ("stage_03_understand.py", "Story Understanding (LLM)"),
    4: ("stage_04_generate_refs.py", "Reference Image Generation"),
    5: ("stage_05_generate_video.py", "Video Clip Generation"),
    6: ("stage_06_lipsync.py", "Lip Sync & Enhancement"),
    7: ("stage_07_assemble.py", "Final Assembly"),
}


def run_stage(stage_num: int, env=None):
    script, description = STAGES[stage_num]
    script_path = Path("src/stages") / script

    print(f"\n{'='*70}")
    print(f"STAGE {stage_num}: {description}")
    print(f"{'='*70}")

    if not script_path.exists():
        print(f"ERROR: {script_path} not found")
        return False

    result = subprocess.run([sys.executable, str(script_path)], env=env)
    return result.returncode == 0


def build_env(drama_dir, episode_dir):
    """Build the subprocess environment, scoping stages to a drama/episode
    if given. Each stage reads these via src/core/path_resolver.py."""
    env = os.environ.copy()
    if drama_dir:
        env["PIPELINE_DRAMA_DIR"] = str(Path(drama_dir).resolve())
    if episode_dir:
        env["PIPELINE_EPISODE_DIR"] = str(Path(episode_dir).resolve())
    return env


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("stage", nargs="?", default=None,
                         help="Stage number (1-7) or 'all'")
    parser.add_argument("--drama-dir", default=None,
                         help="Scope characters/locations/refs to this drama directory")
    parser.add_argument("--episode-dir", default=None,
                         help="Scope audio/transcripts/scenes/clips/video to this episode directory")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help or args.stage is None:
        print("\n" + "="*70)
        print("AUDIO DRAMA TO CINEMA PIPELINE")
        print("="*70)
        print(f"\nUsage: python {sys.argv[0]} <stage_number|all> [--drama-dir DIR] [--episode-dir DIR]")
        print("\nStages:")
        for num, (script, desc) in STAGES.items():
            print(f"  {num}. {desc:40s} ({script})")
        print("\n  all - Run complete pipeline (stops on any error)")
        print("\nExamples:")
        print(f"  python {sys.argv[0]} 1       # Just transcription")
        print(f"  python {sys.argv[0]} all     # Full pipeline (global assets/ and output/)")
        print(f"  python {sys.argv[0]} all --drama-dir dramas/drama_abc --episode-dir dramas/drama_abc/episodes/ep_001")
        print("="*70)
        return

    command = args.stage.lower()
    env = build_env(args.drama_dir, args.episode_dir)

    if command == "all":
        print("\n" + "="*70)
        print("RUNNING FULL PIPELINE")
        print("="*70)
        for num in range(1, 8):
            if not run_stage(num, env=env):
                print(f"\n{'='*70}")
                print(f"PIPELINE HALTED AT STAGE {num}")
                print("="*70)
                sys.exit(1)
        print(f"\n{'='*70}")
        print("FULL PIPELINE COMPLETE")
        print("="*70)
    else:
        try:
            stage_num = int(command)
            if stage_num in STAGES:
                if not run_stage(stage_num, env=env):
                    sys.exit(1)
            else:
                print(f"Invalid stage: {stage_num}. Use 1-7.")
                sys.exit(1)
        except ValueError:
            print(f"Unknown command: {command}")
            sys.exit(1)


if __name__ == "__main__":
    main()
