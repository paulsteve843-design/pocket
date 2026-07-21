"""
Video Generation Engine - produces cinematic clips from shot specifications
Uses LTX-Video with memory optimizations for RTX 3060
Includes fallback to blue frames on generation failure
"""
import json
import torch
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
from diffusers import LTXPipeline, AutoModel
from diffusers.utils import export_to_video
import gc

class VideoGenerator:
    def __init__(self, config):
        self.config = config
        self.device = config.get_device()
        self.pipeline = None
        self._loaded = False
        self.fallback = None  # Will be injected

    def set_fallback_handler(self, fallback_handler):
        """Inject fallback handler for generation failures"""
        self.fallback = fallback_handler

    def load_model(self):
        """Load LTX-Video with aggressive memory optimizations for RTX 3060"""
        if self._loaded:
            return

        print("[VideoGenerator] Loading LTX-Video with memory optimizations...")

        transformer = AutoModel.from_pretrained(
            "Lightricks/LTX-Video",
            subfolder="transformer",
            torch_dtype=torch.bfloat16
        )
        transformer.enable_layerwise_casting(
            storage_dtype=torch.float8_e4m3fn, 
            compute_dtype=torch.bfloat16
        )

        self.pipeline = LTXPipeline.from_pretrained(
            "Lightricks/LTX-Video",
            transformer=transformer,
            torch_dtype=torch.bfloat16
        )

        onload_device = torch.device("cuda")
        offload_device = torch.device("cpu")

        self.pipeline.transformer.enable_group_offload(
            onload_device=onload_device,
            offload_device=offload_device,
            offload_type="leaf_level",
            use_stream=True
        )

        from diffusers.hooks import apply_group_offloading
        apply_group_offloading(
            self.pipeline.text_encoder,
            onload_device=onload_device,
            offload_type="block_level",
            num_blocks_per_group=2
        )
        apply_group_offloading(
            self.pipeline.vae,
            onload_device=onload_device,
            offload_type="leaf_level"
        )

        self.pipeline.vae.enable_tiling()

        self._loaded = True
        print("[VideoGenerator] Model loaded with optimizations")

    def unload_model(self):
        """Free VRAM completely"""
        if self.pipeline:
            del self.pipeline
            self.pipeline = None
        gc.collect()
        torch.cuda.empty_cache()
        self._loaded = False
        print("[VideoGenerator] Model unloaded, VRAM freed")

    def generate_shot(self, shot_spec: Dict, reference_image: Optional[Path] = None,
                       output_path: Path = None, is_narrator: bool = False) -> Path:
        """Generate a single video clip from shot specification"""

        # Skip visual generation for narrator
        if is_narrator and self.fallback:
            print(f"[VideoGenerator] Narrator shot - skipping visual, using placeholder")
            duration = shot_spec.get("duration_estimate", 4.0)
            width, height = self.config.pipeline.video_resolution
            return self.fallback.generate_blue_frame(width, height, duration, output_path=output_path)

        self.load_model()

        prompt = shot_spec.get("visual_prompt", "")
        negative = shot_spec.get("negative_prompt", 
            "worst quality, inconsistent motion, blurry, jittery, distorted, cartoon, anime")

        width, height = self.config.pipeline.video_resolution
        num_frames = self.config.pipeline.video_frames

        # Parse focal length for aspect ratio hint
        focal = shot_spec.get("focal_length", "50mm")
        if "wide" in shot_spec.get("type", "") or "establishing" in shot_spec.get("type", ""):
            width, height = 704, 384
        elif "close" in shot_spec.get("type", ""):
            width, height = 384, 512

        # Load reference image if provided
        image = None
        if reference_image and reference_image.exists():
            image = Image.open(reference_image).convert("RGB")
            image = image.resize((width, height))

        print(f"[VideoGenerator] Generating: {shot_spec.get('type', 'shot')} | {width}x{height} | {num_frames}f")

        try:
            result = self.pipeline(
                prompt=prompt,
                negative_prompt=negative,
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=self.config.pipeline.video_inference_steps,
                guidance_scale=self.config.pipeline.video_guidance_scale,
                decode_timestep=0.03,
                decode_noise_scale=0.025,
                image=image,
            ).frames[0]

            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                export_to_video(result, str(output_path), fps=self.config.pipeline.video_fps)
                print(f"[VideoGenerator] Saved: {output_path}")
                return output_path

            return result

        except (torch.cuda.OutOfMemoryError, RuntimeError, Exception) as e:
            print(f"[VideoGenerator] Generation error: {e}")

            # Try fallback handler
            if self.fallback:
                return self.fallback.handle_generation_failure(shot_spec, e, output_path)

            # Ultimate fallback: simple blue frame
            print("[VideoGenerator] Using emergency blue frame fallback")
            duration = shot_spec.get("duration_estimate", 4.0)
            return self.fallback.generate_blue_frame(width, height, duration, output_path=output_path) if self.fallback else None

    def process_scene_file(self, scene_prompt_path: Path, 
                           character_refs: Dict[str, Path],
                           output_dir: Path,
                           narrator_speakers: List[str] = None):
        """Process all shots from a scene specification file"""
        with open(scene_prompt_path) as f:
            data = json.load(f)

        scene_id = data["scene_id"]
        cinematic = data.get("cinematic_spec", {})
        shots = cinematic.get("shots", [])

        if not shots:
            print(f"[VideoGenerator] No shots for {scene_id}")
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        generated = []

        primary_speaker = data.get("speakers", ["unknown"])[0]
        ref_image = character_refs.get(primary_speaker)

        narrator_speakers = narrator_speakers or []

        for idx, shot in enumerate(shots):
            subject = shot.get("subject", primary_speaker)
            shot_ref = character_refs.get(subject, ref_image)
            is_narrator = subject.upper() in [s.upper() for s in narrator_speakers]

            output_path = output_dir / f"{scene_id}_s{idx:03d}.mp4"

            try:
                result = self.generate_shot(shot, shot_ref, output_path, is_narrator=is_narrator)
                generated.append({
                    "shot_number": idx,
                    "path": str(output_path),
                    "type": shot.get("type", "unknown"),
                    "duration": shot.get("duration_estimate", 4.0),
                    "is_fallback": "fallback" in str(result) if result else False
                })
            except Exception as e:
                print(f"[VideoGenerator] FATAL ERROR shot {idx}: {e}")
                # Last resort: create blue frame
                if self.fallback:
                    width, height = self.config.pipeline.video_resolution
                    duration = shot.get("duration_estimate", 4.0)
                    self.fallback.generate_blue_frame(width, height, duration, output_path=output_path)
                    generated.append({
                        "shot_number": idx,
                        "path": str(output_path),
                        "type": "emergency_fallback",
                        "duration": duration,
                        "is_fallback": True
                    })

            torch.cuda.empty_cache()

        return generated
