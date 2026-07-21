#!/usr/bin/env python3
"""
Pre-flight system check - verifies hardware, dependencies, and model availability
Run this before first pipeline execution
"""
import sys
import subprocess
import json
from pathlib import Path

def check_python():
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"  OK: Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  FAIL: Python {version.major}.{version.minor} (need 3.10+)")
        return False

def check_cuda():
    print("Checking CUDA/PyTorch...")
    try:
        import torch
        print(f"  PyTorch: {torch.__version__}")
        if torch.cuda.is_available():
            print(f"  CUDA available: YES")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            return True
        else:
            print(f"  CUDA available: NO - Will use CPU (very slow)")
            return False
    except ImportError:
        print(f"  FAIL: PyTorch not installed")
        return False

def check_ffmpeg():
    print("Checking FFmpeg...")
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        version_line = result.stdout.split("\n")[0]
        print(f"  OK: {version_line}")
        return True
    except FileNotFoundError:
        print(f"  FAIL: FFmpeg not found in PATH")
        return False

def check_ollama():
    print("Checking Ollama...")
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            models = [line for line in result.stdout.strip().split("\n")[1:] if line.strip()]
            print(f"  OK: Ollama running")
            if models:
                print(f"  Models available: {len(models)}")
                for m in models:
                    print(f"    - {m.split()[0]}")
            else:
                print(f"  WARNING: No models downloaded. Run: ollama pull qwen2.5:7b")
            return True
        else:
            print(f"  FAIL: Ollama not running or not installed")
            return False
    except FileNotFoundError:
        print(f"  FAIL: Ollama not found")
        return False

def check_disk_space():
    print("Checking disk space...")
    import shutil
    total, used, free = shutil.disk_usage(".")
    free_gb = free / (1024**3)
    print(f"  Free space: {free_gb:.1f} GB")
    if free_gb < 50:
        print(f"  WARNING: Less than 50GB free. Models need ~40GB + outputs.")
        return False
    return True

def check_project_structure():
    print("Checking project structure...")
    required = [
        "config/system.yaml",
        "src/core/config_loader.py",
        "src/core/audio_processor.py",
        "src/core/scene_segmenter.py",
        "src/core/story_engine.py",
        "src/core/reference_generator.py",
        "src/core/video_generator.py",
        "src/core/post_processor.py",
        "src/core/fallback_handler.py",
        "src/stages/stage_01_transcribe.py",
        "src/stages/stage_02_segment.py",
        "src/stages/stage_03_understand.py",
        "src/stages/stage_04_generate_refs.py",
        "src/stages/stage_05_generate_video.py",
        "src/stages/stage_06_lipsync.py",
        "src/stages/stage_07_assemble.py",
        "run_pipeline.py",
        "requirements.txt"
    ]

    all_ok = True
    for item in required:
        path = Path(item)
        if path.exists():
            print(f"  OK: {item}")
        else:
            print(f"  FAIL: {item} MISSING")
            all_ok = False

    return all_ok

def check_assets():
    print("Checking asset templates...")
    assets = ["assets/characters.json", "assets/locations.json"]
    for asset in assets:
        path = Path(asset)
        if path.exists():
            print(f"  OK: {asset} (template present)")
        else:
            print(f"  FAIL: {asset} MISSING")

    input_dir = Path("assets/input")
    audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3")) +                   list(input_dir.glob("*.flac")) + list(input_dir.glob("*.m4a"))
    if audio_files:
        print(f"  OK: Found {len(audio_files)} audio file(s)")
    else:
        print(f"  INFO: No audio files in assets/input/ yet")

    return True

def main():
    print("=" * 60)
    print("AUDIO DRAMA TO CINEMA - SYSTEM CHECK")
    print("=" * 60)
    print()

    checks = [
        ("Python", check_python),
        ("CUDA/PyTorch", check_cuda),
        ("FFmpeg", check_ffmpeg),
        ("Ollama", check_ollama),
        ("Disk Space", check_disk_space),
        ("Project Structure", check_project_structure),
        ("Assets", check_assets),
    ]

    results = {}
    for name, check_fn in checks:
        print(f"\n[{name}]")
        try:
            results[name] = check_fn()
        except Exception as e:
            print(f"  ERROR: {e}")
            results[name] = False

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    critical = ["Python", "Project Structure"]
    warnings = ["CUDA/PyTorch", "FFmpeg", "Ollama", "Disk Space"]

    critical_ok = all(results.get(c, False) for c in critical)
    warnings_ok = all(results.get(w, True) for w in warnings)

    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        marker = "OK" if ok else "XX"
        print(f"  [{marker}] {name:20s} {status}")

    print(f"\n{'='*60}")
    if critical_ok and warnings_ok:
        print("ALL CHECKS PASSED - Ready to run pipeline")
        print(f"{'='*60}")
        print("\nNext steps:")
        print("  1. Edit assets/characters.json with your characters")
        print("  2. Edit assets/locations.json with your settings")
        print("  3. Place audio in assets/input/")
        print("  4. Run: python run_pipeline.py all")
        return 0
    elif critical_ok:
        print("CRITICAL CHECKS PASSED - Some warnings present")
        print(f"{'='*60}")
        print("\nWarnings may cause issues but pipeline can still run.")
        print("Review warnings above before proceeding.")
        return 0
    else:
        print("CRITICAL CHECKS FAILED - Fix before running pipeline")
        print(f"{'='*60}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
