"""
Configuration loader with hardware-aware defaults for RTX 3060 Laptop (6GB)
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import torch

@dataclass
class HardwareConfig:
    device: str = "cuda"
    gpu_id: int = 0
    max_vram_gb: float = 5.0
    max_ram_gb: float = 14.0
    mixed_precision: str = "fp16"
    enable_cpu_offload: bool = True
    enable_attention_slicing: bool = True
    enable_vae_slicing: bool = True
    enable_vae_tiling: bool = True

@dataclass
class ModelConfig:
    whisper_model: str = "openai/whisper-medium"
    diarization_model: str = "pyannote/speaker-diarization-3.1"
    llm_model: str = "qwen2.5:7b"
    image_model: str = "black-forest-labs/FLUX.1-schnell"
    video_model: str = "Lightricks/LTX-Video"
    lipsync_model: str = "wav2lip_gan"
    face_enhance_model: str = "GFPGANv1.4"
    upscaler_model: str = "RealESRGAN_x4plus"

@dataclass
class PipelineConfig:
    min_scene_duration: float = 3.0
    max_scene_duration: float = 45.0
    silence_threshold: float = 0.5
    max_shots_per_scene: int = 5
    default_shot_duration: float = 3.0
    video_resolution: List[int] = field(default_factory=lambda: [384, 256])
    video_fps: int = 25
    video_frames: int = 17
    video_inference_steps: int = 20
    video_guidance_scale: float = 2.0

class ConfigManager:
    def __init__(self, config_path: str = "config/system.yaml"):
        self.config_path = Path(config_path)
        self.hardware = HardwareConfig()
        self.models = ModelConfig()
        self.pipeline = PipelineConfig()
        self.paths = {}
        self.fallback = {}
        self._load()

    def _load(self):
        if not self.config_path.exists():
            return
        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        if "hardware" in data:
            for k, v in data["hardware"].items():
                if hasattr(self.hardware, k):
                    setattr(self.hardware, k, v)

        if "models" in data:
            for k, v in data["models"].items():
                if hasattr(self.models, k):
                    setattr(self.models, k, v)

        if "pipeline" in data:
            for k, v in data["pipeline"].items():
                if hasattr(self.pipeline, k):
                    setattr(self.pipeline, k, v)
            # Handle nested fallback config
            if "fallback" in data["pipeline"]:
                self.fallback = data["pipeline"]["fallback"]
            if "scene" in data["pipeline"]:
                for k, v in data["pipeline"]["scene"].items():
                    if hasattr(self.pipeline, k):
                        setattr(self.pipeline, k, v)
            if "shot" in data["pipeline"]:
                for k, v in data["pipeline"]["shot"].items():
                    if hasattr(self.pipeline, k):
                        setattr(self.pipeline, k, v)

        if "paths" in data:
            self.paths = data["paths"]

    def get_device(self) -> torch.device:
        if self.hardware.device == "cuda" and torch.cuda.is_available():
            return torch.device(f"cuda:{self.hardware.gpu_id}")
        return torch.device("cpu")

    def get_path(self, name: str) -> Path:
        return Path(self.paths.get(name, name))

    def can_fit_model(self, model_vram_gb: float) -> bool:
        return model_vram_gb <= self.hardware.max_vram_gb
