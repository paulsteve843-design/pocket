"""
Continuity tracking system - ensures props, costumes, lighting remain consistent
across scenes and shots
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class PropState:
    name: str
    location: str  # "in_hand_sarah", "on_table", "floor", "broken", etc.
    condition: str  # "new", "worn", "damaged", "broken"
    last_seen_scene: str

@dataclass
class CharacterState:
    name: str
    outfit: str
    expression: str
    emotional_state: str
    physical_state: str  # "uninjured", "bruised", "bleeding", etc.
    last_seen_scene: str

@dataclass
class LightingState:
    location: str
    time_of_day: str
    key_light: str
    fill_level: str
    mood: str

class ContinuityTracker:
    def __init__(self):
        self.props: Dict[str, PropState] = {}
        self.characters: Dict[str, CharacterState] = {}
        self.lighting: Dict[str, LightingState] = {}
        self.scene_history: List[str] = []

    def initialize_from_definitions(self, characters_path: Path, props_path: Path):
        """Load initial states from definition files"""
        if characters_path.exists():
            with open(characters_path) as f:
                chars = json.load(f)
            for name, data in chars.items():
                self.characters[name] = CharacterState(
                    name=name,
                    outfit=data.get("clothing", "unknown"),
                    expression=data.get("expression", "neutral"),
                    emotional_state=data.get("emotion", "neutral"),
                    physical_state="uninjured",
                    last_seen_scene="initial"
                )

        if props_path.exists():
            with open(props_path) as f:
                props = json.load(f)
            for name, data in props.items():
                self.props[name] = PropState(
                    name=name,
                    location=data.get("first_appearance", "unknown"),
                    condition="new",
                    last_seen_scene="initial"
                )

    def update_after_scene(self, scene_id: str, scene_data: Dict):
        """Update continuity state after processing a scene"""
        self.scene_history.append(scene_id)

        # Check for prop state changes in dialogue/action
        dialogue_text = " ".join([d["text"] for d in scene_data.get("dialogue", [])])

        # Simple keyword-based prop tracking
        for prop_name, prop in self.props.items():
            if prop_name.replace("_", " ") in dialogue_text.lower():
                # Detect state changes
                if any(word in dialogue_text.lower() for word in ["drop", "fall", "break", "shatter"]):
                    prop.condition = "damaged"
                if any(word in dialogue_text.lower() for word in ["pick up", "grab", "take", "hold"]):
                    speaker = scene_data.get("dialogue", [{}])[0].get("speaker", "unknown")
                    prop.location = f"in_hand_{speaker}"

                prop.last_seen_scene = scene_id

        # Update character emotional states based on mood
        mood = scene_data.get("mood", "neutral")
        for char_name, char in self.characters.items():
            if char_name in [d.get("speaker", "") for d in scene_data.get("dialogue", [])]:
                char.emotional_state = mood
                char.last_seen_scene = scene_id

    def validate_shot(self, shot_spec: Dict, scene_id: str) -> List[str]:
        """Check a shot specification for continuity errors"""
        issues = []

        # Check prop continuity
        for prop_name, prop in self.props.items():
            if prop_name in str(shot_spec).lower():
                if prop.condition == "broken" and "intact" in str(shot_spec).lower():
                    issues.append(f"CONTINUITY: {prop_name} is broken but shown intact in {scene_id}")

        # Check character outfit consistency
        subject = shot_spec.get("subject", "")
        if subject in self.characters:
            char = self.characters[subject]
            blocking = shot_spec.get("blocking", "")
            if char.outfit.lower() not in blocking.lower() and len(blocking) > 10:
                issues.append(f"CONTINUITY: {subject} outfit mismatch in {scene_id} (expected: {char.outfit})")

        return issues

    def save_state(self, output_path: Path):
        """Save current continuity state"""
        state = {
            "scene_history": self.scene_history,
            "props": {k: asdict(v) for k, v in self.props.items()},
            "characters": {k: asdict(v) for k, v in self.characters.items()},
            "lighting": {k: asdict(v) for k, v in self.lighting.items()}
        }
        with open(output_path, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self, state_path: Path):
        """Load continuity state from file"""
        with open(state_path) as f:
            state = json.load(f)
        self.scene_history = state.get("scene_history", [])
        # Reconstruct objects from dicts
        self.props = {k: PropState(**v) for k, v in state.get("props", {}).items()}
        self.characters = {k: CharacterState(**v) for k, v in state.get("characters", {}).items()}
        self.lighting = {k: LightingState(**v) for k, v in state.get("lighting", {}).items()}
