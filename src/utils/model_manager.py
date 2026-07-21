"""
Model download and management utilities
"""
import os
from pathlib import Path
from typing import Dict, List
import subprocess

class ModelManager:
    """Manages model downloads and verification"""

    REQUIRED_MODELS = {
        "whisper": {
            "source": "openai/whisper-medium",
            "size_gb": 1.5,
            "auto_download": True
        },
        "diarization": {
            "source": "pyannote/speaker-diarization-3.1",
            "size_gb": 2.0,
            "auto_download": True,
            "requires_auth": True  # Requires HuggingFace token
        },
        "flux": {
            "source": "black-forest-labs/FLUX.1-schnell",
            "size_gb": 23.0,
            "auto_download": True,
            "requires_auth": True
        },
        "ltx_video": {
            "source": "Lightricks/LTX-Video",
            "size_gb": 9.0,
            "auto_download": True
        },
        "qwen": {
            "source": "qwen2.5:7b",
            "size_gb": 4.0,
            "auto_download": False,  # Via Ollama
            "install_cmd": "ollama pull qwen2.5:7b"
        }
    }

    def __init__(self, models_dir: Path = Path("models")):
        self.models_dir = models_dir
        self.models_dir.mkdir(exist_ok=True)

    def check_disk_space(self, required_gb: float = 50.0) -> bool:
        """Check if enough disk space is available"""
        stat = os.statvfs(self.models_dir)
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        return available_gb >= required_gb

    def verify_models(self) -> Dict[str, bool]:
        """Check which models are already downloaded"""
        status = {}
        # Check HuggingFace cache
        hf_cache = Path.home() / ".cache" / "huggingface"

        for name, info in self.REQUIRED_MODELS.items():
            if info["source"].startswith("qwen"):
                # Check Ollama
                result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True, text=True
                )
                status[name] = info["source"] in result.stdout
            else:
                # Check HF cache
                model_path = hf_cache / "hub" / f"models--{info['source'].replace('/', '--')}"
                status[name] = model_path.exists()

        return status

    def print_status(self):
        """Print model download status"""
        status = self.verify_models()
        total_required = sum(info["size_gb"] for info in self.REQUIRED_MODELS.values())

        print(f"{'='*60}")
        print("MODEL STATUS")
        print(f"{'='*60}")
        print(f"{'Model':<20} {'Status':<12} {'Size':<10} {'Source'}")
        print(f"{'-'*60}")

        for name, info in self.REQUIRED_MODELS.items():
            downloaded = status.get(name, False)
            status_str = "DOWNLOADED" if downloaded else "MISSING"
            print(f"{name:<20} {status_str:<12} {info['size_gb']:<10.1f}GB {info['source']}")

        print(f"{'-'*60}")
        print(f"Total required: {total_required:.1f}GB")

        if not self.check_disk_space(total_required):
            print(f"WARNING: Insufficient disk space. Need {total_required:.1f}GB free.")

        print(f"{'='*60}")

        # Print auth requirements
        auth_needed = [name for name, info in self.REQUIRED_MODELS.items() if info.get("requires_auth") and not status.get(name)]
        if auth_needed:
            print("\nModels requiring HuggingFace authentication:")
            for name in auth_needed:
                print(f"  - {name}: {self.REQUIRED_MODELS[name]['source']}")
            print("\nSet your token: export HF_TOKEN=your_token_here")
            print("Get token: https://huggingface.co/settings/tokens")

    def download_ollama_model(self, model_name: str = "qwen2.5:7b"):
        """Download LLM via Ollama"""
        print(f"Downloading {model_name} via Ollama...")
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"{model_name} downloaded successfully")
