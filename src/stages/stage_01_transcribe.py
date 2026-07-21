#!/usr/bin/env python3
"""Stage 1: Audio ingestion and transcription with speaker diarization"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import ConfigManager
from core.audio_processor import AudioProcessor
from core.path_resolver import episode_path, is_scoped

def main():
    config = ConfigManager("config/system.yaml")
    processor = AudioProcessor(config)

    # When invoked from the web studio, PIPELINE_EPISODE_DIR points at
    # dramas/<id>/episodes/ep_NNN/, where the uploaded audio actually lives.
    # Otherwise fall back to the original global assets/input folder.
    input_dir = episode_path(".", config.paths.get("input", "assets/input"))
    output_dir = episode_path("output/transcripts", Path(config.paths.get("output", "output")) / "transcripts")
    output_dir.mkdir(parents=True, exist_ok=True)

    if is_scoped():
        print(f"Running scoped to episode dir: {input_dir}")

    audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3")) +                   list(input_dir.glob("*.flac")) + list(input_dir.glob("*.m4a"))

    if not audio_files:
        print("=" * 60)
        print("NO AUDIO FILES FOUND")
        print("=" * 60)
        print(f"\nPlace your audio drama file in: {input_dir.absolute()}")
        print("Supported formats: WAV, MP3, FLAC, M4A")
        print("\nThen rerun: python run_pipeline.py 1")
        return

    for audio_file in audio_files:
        print(f"\n{'='*60}")
        print(f"PROCESSING: {audio_file.name}")
        print(f"{'='*60}")

        transcript = processor.transcribe(audio_file)
        output_path = output_dir / f"{audio_file.stem}.json"
        processor.save_transcript(transcript, output_path)

        # Print speaker summary
        speakers = transcript.get("unique_speakers", [])
        print(f"\n{'─'*60}")
        print(f"DETECTED {len(speakers)} SPEAKERS:")
        print(f"{'─'*60}")
        for spk, info in transcript.get("speaker_summary", {}).items():
            print(f"  {spk:15s} | {info['segments']:3d} segments | {info['words']:4d} words | {info['duration']:6.1f}s")

        print(f"\n{'─'*60}")
        print("NEXT STEPS:")
        print("  1. Review the transcript in output/transcripts/")
        print("  2. Identify which speakers are characters vs narrators")
        print("  3. Create assets/characters.json with descriptions")
        print("  4. Create assets/locations.json with settings")
        print(f"{'─'*60}")

    processor.unload_models()
    print(f"\n{'='*60}")
    print("STAGE 1 COMPLETE")
    print(f"{'='*60}")
    if not is_scoped():
        print("Run: python run_pipeline.py 2")

if __name__ == "__main__":
    main()
