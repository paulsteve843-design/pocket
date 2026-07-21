"""
User Reference Image Integrator
Blends user-uploaded photos with AI-generated references for character consistency
"""
import json
import torch
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
import numpy as np

class UserReferenceIntegrator:
    """Integrates user-uploaded reference images into the pipeline"""

    def __init__(self, config):
        self.config = config
        self.device = config.get_device()

    def load_user_reference(self, image_path: Path) -> Optional[Image.Image]:
        """Load and validate user-uploaded reference image"""
        try:
            img = Image.open(image_path).convert("RGB")

            # Validate size
            width, height = img.size
            if width < 256 or height < 256:
                print(f"Warning: Reference image too small ({width}x{height}), minimum 256x256 recommended")
                return None

            # Resize to standard reference size
            img = img.resize((512, 768))

            return img
        except Exception as e:
            print(f"Error loading reference image {image_path}: {e}")
            return None

    def blend_with_ai_reference(self, user_image: Image.Image, ai_prompt: str, 
                                 output_path: Path) -> Path:
        """
        Blend user photo with AI-generated reference
        Uses IP-Adapter or similar technique to maintain user likeness
        while matching the cinematic style
        """
        # For now, save user image as primary reference
        # In production, this would use IP-Adapter or similar
        output_path.parent.mkdir(parents=True, exist_ok=True)
        user_image.save(output_path)

        print(f"Saved user reference: {output_path}")
        return output_path

    def generate_character_from_user_ref(self, user_image_path: Path, 
                                          character_data: Dict,
                                          output_dir: Path) -> List[Path]:
        """
        Generate multiple reference angles from single user photo
        Uses the user photo as base, generates variations
        """
        user_img = self.load_user_reference(user_image_path)
        if not user_img:
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        generated = []

        # Save original as primary reference
        primary = output_dir / f"{character_data['name'].lower().replace(' ', '_')}_user_primary.png"
        user_img.save(primary)
        generated.append(primary)

        # Generate variations (frontal, profile, 3/4 view)
        # This would use a face rotation model or ControlNet in production
        # For now, we save the same image with different prompts for later generation

        views = ["frontal", "profile", "three_quarter"]
        for view in views:
            view_path = output_dir / f"{character_data['name'].lower().replace(' ', '_')}_{view}.png"
            user_img.save(view_path)
            generated.append(view_path)

        return generated

    def create_character_embedding(self, user_image_paths: List[Path]) -> Optional[torch.Tensor]:
        """
        Create a face embedding from user reference images
        Used for consistency across episodes
        """
        try:
            from transformers import CLIPProcessor, CLIPModel

            model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

            embeddings = []
            for img_path in user_image_paths:
                image = Image.open(img_path).convert("RGB")
                inputs = processor(images=image, return_tensors="pt")

                with torch.no_grad():
                    image_features = model.get_image_features(**inputs)
                    embeddings.append(image_features)

            # Average embeddings
            if embeddings:
                avg_embedding = torch.mean(torch.stack(embeddings), dim=0)
                return avg_embedding

        except Exception as e:
            print(f"Error creating embedding: {e}")

        return None

    def verify_character_consistency(self, generated_image: Image.Image, 
                                     reference_embedding: torch.Tensor) -> float:
        """
        Verify that a generated image matches the character reference
        Returns similarity score (0-1)
        """
        try:
            from transformers import CLIPProcessor, CLIPModel

            model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

            inputs = processor(images=generated_image, return_tensors="pt")
            with torch.no_grad():
                gen_features = model.get_image_features(**inputs)

            # Cosine similarity
            similarity = torch.nn.functional.cosine_similarity(
                reference_embedding, gen_features
            ).item()

            return similarity

        except Exception as e:
            print(f"Error verifying consistency: {e}")
            return 0.0

    def process_user_uploads(self, drama_id: str, user_uploads_dir: Path,
                            character_registry: Dict) -> Dict[str, List[Path]]:
        """
        Process all user-uploaded references for a drama
        Returns mapping of character_id -> list of processed reference paths
        """
        results = {}

        if not user_uploads_dir.exists():
            return results

        for img_file in user_uploads_dir.glob("*"):
            # Parse filename: character_name_user_ref.jpg
            stem = img_file.stem
            if "_user_ref" in stem or "_ref" in stem:
                char_name = stem.replace("_user_ref", "").replace("_ref", "").replace("_", " ").upper()

                # Find matching character in registry
                char_id = None
                for cid, cdata in character_registry.items():
                    if cdata.get("name", "").upper() == char_name or cid == char_name.replace(" ", "_"):
                        char_id = cid
                        break

                if char_id:
                    refs_dir = user_uploads_dir.parent / "refs"
                    processed = self.generate_character_from_user_ref(
                        img_file, 
                        {"name": char_name},
                        refs_dir
                    )
                    results[char_id] = processed

                    # Update registry
                    character_registry[char_id]["user_uploaded"] = True
                    character_registry[char_id]["reference_images"] = [str(p) for p in processed]

        return results
