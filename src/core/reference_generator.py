"""
Reference Image Generator - creates consistent character and location references
Uses FLUX.1-schnell with quantization for RTX 3060
"""
import json
import torch
from pathlib import Path
from typing import Dict, List
from PIL import Image
from diffusers import FluxPipeline
import gc

class ReferenceGenerator:
    def __init__(self, config):
        self.config = config
        self.device = config.get_device()
        self.pipeline = None
        self._loaded = False

    def load_model(self):
        """Load FLUX.1-schnell with memory optimizations"""
        if self._loaded:
            return

        print("[ReferenceGenerator] Loading FLUX.1-schnell...")

        self.pipeline = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell",
            torch_dtype=torch.bfloat16
        )

        # Enable memory optimizations
        self.pipeline.enable_attention_slicing(1)
        self.pipeline.enable_vae_slicing()

        # For RTX 3060, use sequential CPU offloading if needed
        if self.config.hardware.enable_cpu_offload:
            self.pipeline.enable_sequential_cpu_offload()
        else:
            self.pipeline = self.pipeline.to(self.device)

        self._loaded = True
        print("[ReferenceGenerator] Model loaded")

    def unload_model(self):
        """Free VRAM"""
        if self.pipeline:
            del self.pipeline
            self.pipeline = None
        gc.collect()
        torch.cuda.empty_cache()
        self._loaded = False

    def generate_character_reference(self, name: str, definition: Dict, 
                                      output_dir: Path) -> Path:
        """Generate a consistent character reference image"""
        self.load_model()

        appearance = definition.get("appearance", "")
        clothing = definition.get("clothing", "")
        expression = definition.get("expression", "neutral")

        prompt = f"""Cinematic character portrait of {name}. {appearance}. 
        Wearing {clothing}. {expression} expression. 
        Front-facing, shoulders up, neutral studio lighting, sharp focus, 
        85mm lens, photorealistic, 8k, highly detailed skin texture, 
        character reference sheet, consistent facial features"""

        negative = "cartoon, anime, illustration, painting, sketch, deformed, blurry, inconsistent features, multiple faces, watermark, text"

        print(f"[ReferenceGenerator] Generating character: {name}")

        image = self.pipeline(
            prompt=prompt,
            negative_prompt=negative,
            num_inference_steps=4,  # schnell is fast
            guidance_scale=0.0,
            height=768,
            width=512
        ).images[0]

        output_path = output_dir / f"character_{name.lower().replace(' ', '_')}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)

        print(f"[ReferenceGenerator] Saved: {output_path}")
        return output_path

    def generate_location_reference(self, name: str, definition: Dict,
                                     output_dir: Path) -> Path:
        """Generate a location establishing shot reference"""
        self.load_model()

        description = definition.get("description", "")
        lighting = definition.get("lighting", "neutral")
        time = definition.get("time_of_day", "day")
        atmosphere = definition.get("atmosphere", "")

        prompt = f"""Cinematic establishing shot of {name}. {description}. 
        {lighting} lighting. Time of day: {time}. {atmosphere}.
        Wide angle, 24mm lens, atmospheric perspective, film grain, 
        photorealistic environment, highly detailed, 8k"""

        negative = "cartoon, anime, illustration, people, characters, faces, watermark, text, blurry"

        print(f"[ReferenceGenerator] Generating location: {name}")

        image = self.pipeline(
            prompt=prompt,
            negative_prompt=negative,
            num_inference_steps=4,
            guidance_scale=0.0,
            height=512,
            width=768
        ).images[0]

        output_path = output_dir / f"location_{name.lower().replace(' ', '_')}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)

        print(f"[ReferenceGenerator] Saved: {output_path}")
        return output_path

    def generate_all_references(self, characters_path: Path,
                                locations_path: Path,
                                output_dir: Path) -> Dict[str, Path]:
        """Generate all reference images from definition files.

        If a definition includes a "reference_image" pointing at a file that
        exists (e.g. the user uploaded one via the studio UI), that image is
        copied into output_dir instead of generating a new one with FLUX.
        This is what makes "Upload Ref" in the UI actually take effect.
        """
        import shutil
        output_dir.mkdir(parents=True, exist_ok=True)
        references = {}

        def use_user_reference(name: str, definition: Dict, prefix: str) -> Path:
            user_ref = definition.get("reference_image")
            if not user_ref:
                return None
            user_ref_path = Path(user_ref)
            if not user_ref_path.exists():
                print(f"[ReferenceGenerator] User reference for {name} not found at {user_ref_path}, generating instead")
                return None
            dest = output_dir / f"{prefix}_{name.lower().replace(' ', '_')}{user_ref_path.suffix}"
            shutil.copy(user_ref_path, dest)
            print(f"[ReferenceGenerator] Using user-uploaded reference for {name}: {dest}")
            return dest

        # Generate character references
        if characters_path.exists():
            with open(characters_path) as f:
                characters = json.load(f)

            print(f"[ReferenceGenerator] Processing {len(characters)} characters...")
            for name, definition in characters.items():
                path = use_user_reference(name, definition, "character")
                if path is None:
                    path = self.generate_character_reference(name, definition, output_dir)
                    torch.cuda.empty_cache()
                references[f"char_{name}"] = path

        # Generate location references
        if locations_path.exists():
            with open(locations_path) as f:
                locations = json.load(f)

            print(f"[ReferenceGenerator] Processing {len(locations)} locations...")
            for name, definition in locations.items():
                path = use_user_reference(name, definition, "location")
                if path is None:
                    path = self.generate_location_reference(name, definition, output_dir)
                    torch.cuda.empty_cache()
                references[f"loc_{name}"] = path

        return references
