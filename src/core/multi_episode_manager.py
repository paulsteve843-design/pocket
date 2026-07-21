"""
Multi-Episode Drama Manager
Handles multiple dramas, multiple episodes, character persistence, language detection
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import shutil

@dataclass
class DramaMetadata:
    drama_id: str
    title: str
    language: str           # auto-detected: "en", "ta", "hi", etc.
    theme: str              # auto-detected: "romance", "thriller", "horror", etc.
    total_episodes: int
    current_episode: int
    created_at: str

@dataclass
class CharacterIdentity:
    character_id: str       # persistent ID across all episodes
    name: str
    role: str
    appearance: str
    clothing: str
    expression: str
    voice_signature: str    # hash of voice characteristics for recognition
    reference_images: List[str]  # paths to reference images
    user_uploaded: bool     # whether user provided a reference photo
    first_seen_episode: int
    last_seen_episode: int
    episode_count: int      # how many episodes this character appears in

@dataclass
class EpisodeState:
    episode_id: str
    drama_id: str
    episode_number: int
    audio_path: str
    transcript_path: Optional[str]
    scenes_path: Optional[str]
    prompts_path: Optional[str]
    clips_dir: Optional[str]
    final_video_path: Optional[str]
    status: str             # "pending", "transcribed", "segmented", "prompted", "generated", "complete"
    continuity_snapshot: Dict  # character states, prop states at end of episode

class MultiEpisodeManager:
    def __init__(self, base_dir: Path = Path("dramas")):
        self.base_dir = base_dir
        self.base_dir.mkdir(exist_ok=True)
        self.current_drama = None

    def create_drama(self, title: str, language: str = "auto", theme: str = "auto") -> str:
        """Initialize a new drama series"""
        drama_id = f"drama_{self._generate_id(title)}"
        drama_dir = self.base_dir / drama_id

        # Create directory structure
        for subdir in ["characters/refs", "characters/user_uploads", "locations/refs", "episodes"]:
            (drama_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = {
            "drama_id": drama_id,
            "title": title,
            "language": language,
            "theme": theme,
            "total_episodes": 0,
            "current_episode": 0,
            "created_at": str(datetime.now()),
            "status": "active"
        }

        with open(drama_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Initialize empty registries
        with open(drama_dir / "characters" / "character_registry.json", "w") as f:
            json.dump({}, f, indent=2)

        with open(drama_dir / "locations" / "location_registry.json", "w") as f:
            json.dump({}, f, indent=2)

        with open(drama_dir / "continuity_state.json", "w") as f:
            json.dump({"episode_states": [], "character_aging": {}, "prop_states": {}}, f, indent=2)

        print(f"Created new drama: {title} ({drama_id})")
        return drama_id

    def add_episode(self, drama_id: str, audio_path: Path, episode_number: Optional[int] = None) -> str:
        """Add a new episode to an existing drama"""
        drama_dir = self.base_dir / drama_id
        if not drama_dir.exists():
            raise ValueError(f"Drama {drama_id} not found")

        # Load metadata
        with open(drama_dir / "metadata.json") as f:
            metadata = json.load(f)

        # Determine episode number
        if episode_number is None:
            episode_number = metadata["total_episodes"] + 1

        episode_id = f"ep_{episode_number:03d}"
        episode_dir = drama_dir / "episodes" / episode_id
        episode_dir.mkdir(parents=True, exist_ok=True)

        # Copy audio to episode directory
        dest_audio = episode_dir / f"audio{audio_path.suffix}"
        shutil.copy(audio_path, dest_audio)

        # Create episode state
        episode_state = {
            "episode_id": episode_id,
            "drama_id": drama_id,
            "episode_number": episode_number,
            "audio_path": str(dest_audio),
            "transcript_path": None,
            "scenes_path": None,
            "prompts_path": None,
            "clips_dir": None,
            "final_video_path": None,
            "status": "pending",
            "continuity_snapshot": {}
        }

        with open(episode_dir / "state.json", "w") as f:
            json.dump(episode_state, f, indent=2)

        # Update metadata
        metadata["total_episodes"] = max(metadata["total_episodes"], episode_number)
        metadata["current_episode"] = episode_number
        with open(drama_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"Added episode {episode_number} to {drama_id}")
        return episode_id

    def get_character_registry(self, drama_id: str) -> Dict:
        """Get current character registry for a drama"""
        path = self.base_dir / drama_id / "characters" / "character_registry.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def update_character_registry(self, drama_id: str, characters: Dict):
        """Update character registry (merge with existing)"""
        path = self.base_dir / drama_id / "characters" / "character_registry.json"
        existing = self.get_character_registry(drama_id)

        # Merge: update existing characters, add new ones
        for char_id, char_data in characters.items():
            if char_id in existing:
                # Update episode tracking
                existing[char_id]["last_seen_episode"] = char_data.get("last_seen_episode", existing[char_id].get("last_seen_episode", 1))
                existing[char_id]["episode_count"] = existing[char_id].get("episode_count", 0) + 1
                # Update appearance if changed (character aging, costume changes)
                if "appearance" in char_data and char_data["appearance"] != existing[char_id].get("appearance", ""):
                    existing[char_id]["appearance"] = char_data["appearance"]
                    existing[char_id]["appearance_history"] = existing[char_id].get("appearance_history", []) + [{
                        "episode": char_data.get("last_seen_episode", 1),
                        "appearance": char_data["appearance"]
                    }]
            else:
                existing[char_id] = char_data

        with open(path, "w") as f:
            json.dump(existing, f, indent=2)

    def add_user_reference(self, drama_id: str, character_name: str, image_path: Path):
        """Add a user-uploaded reference image for a character"""
        user_uploads_dir = self.base_dir / drama_id / "characters" / "user_uploads"
        user_uploads_dir.mkdir(exist_ok=True)

        dest = user_uploads_dir / f"{character_name.lower().replace(' ', '_')}_user_ref{image_path.suffix}"
        shutil.copy(image_path, dest)

        # Update character registry
        registry = self.get_character_registry(drama_id)
        char_id = character_name.upper().replace(" ", "_")
        if char_id in registry:
            registry[char_id]["user_uploaded"] = True
            registry[char_id]["reference_images"] = registry[char_id].get("reference_images", []) + [str(dest)]
            self.update_character_registry(drama_id, registry)

        print(f"Added user reference for {character_name}: {dest}")
        return dest

    def get_episode_continuity(self, drama_id: str, episode_number: int) -> Dict:
        """Get continuity state from previous episode"""
        drama_dir = self.base_dir / drama_id
        continuity_path = drama_dir / "continuity_state.json"

        if continuity_path.exists():
            with open(continuity_path) as f:
                state = json.load(f)

            # Find the state from the previous episode
            for ep_state in state.get("episode_states", []):
                if ep_state.get("episode_number") == episode_number - 1:
                    return ep_state.get("continuity_snapshot", {})

        return {}

    def save_episode_continuity(self, drama_id: str, episode_number: int, snapshot: Dict):
        """Save continuity snapshot after episode processing"""
        continuity_path = self.base_dir / drama_id / "continuity_state.json"

        with open(continuity_path) as f:
            state = json.load(f)

        state["episode_states"].append({
            "episode_number": episode_number,
            "continuity_snapshot": snapshot,
            "timestamp": str(datetime.now())
        })

        with open(continuity_path, "w") as f:
            json.dump(state, f, indent=2)

    def list_dramas(self) -> List[Dict]:
        """List all dramas"""
        dramas = []
        for drama_dir in self.base_dir.iterdir():
            if drama_dir.is_dir() and (drama_dir / "metadata.json").exists():
                with open(drama_dir / "metadata.json") as f:
                    dramas.append(json.load(f))
        return dramas

    def list_episodes(self, drama_id: str) -> List[Dict]:
        """List all episodes for a drama"""
        episodes = []
        episodes_dir = self.base_dir / drama_id / "episodes"
        if episodes_dir.exists():
            for ep_dir in sorted(episodes_dir.iterdir()):
                state_file = ep_dir / "state.json"
                if state_file.exists():
                    with open(state_file) as f:
                        episodes.append(json.load(f))
        return episodes

    def _generate_id(self, title: str) -> str:
        """Generate a short unique ID from title"""
        hash_obj = hashlib.md5(title.encode())
        return hash_obj.hexdigest()[:8]

from datetime import datetime
