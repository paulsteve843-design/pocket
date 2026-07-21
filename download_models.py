#!/usr/bin/env python3
"""
Pre-download all required models before running pipeline
Saves time during actual production
"""
import sys
import subprocess
from pathlib import Path

def download_ollama_model():
    print("=" * 60)
    print("Downloading Qwen 7B via Ollama...")
    print("=" * 60)
    try:
        subprocess.run(["ollama", "pull", "qwen2.5:7b"], check=True)
        print("OK: Qwen 7B downloaded")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FAIL: {e}")
        return False
    except FileNotFoundError:
        print("FAIL: Ollama not installed. Download from https://ollama.com")
        return False

def download_whisper():
    print("\n" + "=" * 60)
    print("Downloading Whisper Medium...")
    print("=" * 60)
    try:
        import whisper
        model = whisper.load_model("medium")
        print("OK: Whisper Medium downloaded")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False

def download_flux():
    print("\n" + "=" * 60)
    print("Downloading FLUX.1-schnell...")
    print("=" * 60)
    print("This requires HuggingFace authentication.")
    print("Set token: export HF_TOKEN=your_token_here")
    print("Get token: https://huggingface.co/settings/tokens")
    print()

    try:
        from diffusers import FluxPipeline
        print("Downloading FLUX.1-schnell (23GB, this will take time)...")
        pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell",
            torch_dtype="auto"
        )
        print("OK: FLUX.1-schnell downloaded")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False

def download_ltx():
    print("\n" + "=" * 60)
    print("Downloading LTX-Video...")
    print("=" * 60)

    try:
        from diffusers import LTXPipeline
        print("Downloading LTX-Video (9GB, this will take time)...")
        pipe = LTXPipeline.from_pretrained(
            "Lightricks/LTX-Video",
            torch_dtype="auto"
        )
        print("OK: LTX-Video downloaded")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False

def main():
    print("=" * 60)
    print("MODEL DOWNLOAD UTILITY")
    print("=" * 60)
    print("\nThis will download all required models (~40GB total)")
    print("Models are cached and reused across runs")
    print()

    if input("Continue? (y/n): ").lower() != "y":
        print("Cancelled")
        return

    results = {
        "Ollama/Qwen": download_ollama_model(),
        "Whisper": download_whisper(),
        "FLUX": download_flux(),
        "LTX-Video": download_ltx(),
    }

    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    for name, ok in results.items():
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")

    if all(results.values()):
        print("\nAll models ready. You can now run the pipeline.")
    else:
        print("\nSome models failed. Fix issues and rerun this script.")

if __name__ == "__main__":
    main()
