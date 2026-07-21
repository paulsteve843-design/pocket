"""
Story Understanding Engine - converts scenes into cinematic shot specifications
Uses local LLM (Ollama/Qwen) for narrative-to-visual translation
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import ollama

class StoryEngine:
    def __init__(self, config):
        self.config = config
        self.model = config.models.llm_model
        self._character_registry = {}
        self._location_registry = {}
        self._prop_registry = {}

    def load_character_registry(self, path: Path):
        """Load character definitions from JSON"""
        if path.exists():
            with open(path) as f:
                self._character_registry = json.load(f)

    def load_location_registry(self, path: Path):
        """Load location definitions from JSON"""
        if path.exists():
            with open(path) as f:
                self._location_registry = json.load(f)

    def load_prop_registry(self, path: Path):
        """Load prop definitions from JSON"""
        if path.exists():
            with open(path) as f:
                self._prop_registry = json.load(f)

    def _build_system_prompt(self) -> str:
        return """You are a cinematographer and storyboard artist with 30 years of experience.
Your task: convert audio drama scenes into detailed visual shot specifications.

CRITICAL RULES:
1. Preserve ALL dialogue exactly as written - never paraphrase or summarize
2. Infer camera angles, lighting, and blocking from subtext and emotion
3. Use provided character descriptions for visual consistency
4. Use provided location descriptions for environment accuracy
5. Flag any ambiguities that require director interpretation
6. Output ONLY valid JSON - no markdown, no explanations

SHOT GRAMMAR:
- close_up: Face fills frame, emotional intensity, 85mm+
- medium_shot: Waist up, dialogue standard, 50mm
- wide_shot: Full body + environment, context, 24-35mm
- over_shoulder: Dialogue interaction, spatial relationship, 50mm
- insert: Object detail, prop focus, 50mm macro
- two_shot: Two characters in frame, relationship, 35mm
- pov: Character's point of view, subjective, any lens
- reaction: Listening character's face, 85mm+
- establishing: Location introduction, wide, 16-24mm

LIGHTING MOODS:
- high_key: Bright, even, optimistic or sterile
- low_key: Deep shadows, dramatic, noir or horror
- natural: Window light, realistic, documentary feel
- neon: Artificial colors, urban night, cyberpunk
- golden_hour: Warm, nostalgic, romantic
- chiaroscuro: Extreme contrast, classical drama

CAMERA MOVEMENT:
- static: Locked off, contemplative, stable
- pan: Horizontal sweep, reveal or follow
- tilt: Vertical sweep, power or vulnerability
- dolly_in: Push forward, intensification
- dolly_out: Pull back, isolation or context
- handheld: Slight shake, urgency or realism
- steadicam: Smooth follow, dreamlike or tracking
- crane: Vertical movement, epic or overview

Output JSON structure:
{
  "shots": [
    {
      "shot_number": 1,
      "type": "close_up",
      "subject": "character_name",
      "focal_length": "85mm",
      "camera_height": "eye_level|low|high|overhead|worm",
      "camera_movement": "static",
      "movement_motivation": "why the camera moves or stays still",
      "lighting": {
        "key_source": "practical lamp window moonlight",
        "mood": "low_key",
        "color_temperature": "warm|cool|neutral|mixed",
        "ratio": "key_to_fill ratio like 8:1 or 2:1"
      },
      "blocking": "character positions and movement in frame",
      "duration_estimate": 4.5,
      "dialogue_covered": ["start_time", "end_time"],
      "visual_prompt": "detailed text-to-image prompt for generation",
      "negative_prompt": "what to avoid in generation",
      "continuity_requirements": ["costume_state", "prop_positions", "lighting_state"],
      "emotional_beats": ["beat1", "beat2"]
    }
  ],
  "scene_mood_arc": "tense_building|romantic_release|suspense_peak|revelation|confrontation|resolution",
  "color_palette": "warm_amber|cool_blue|desaturated|high_contrast|sepia|monochrome",
  "continuity_notes": ["note1", "note2"],
  "director_flags": ["ambiguity1", "interpretation_needed2"]
}"""

    def _build_scene_prompt(self, scene: Dict) -> str:
        # Character context
        char_context = []
        for speaker in scene.get("speakers", []):
            if speaker in self._character_registry:
                c = self._character_registry[speaker]
                char_context.append(f"""
CHARACTER: {speaker}
- Visual: {c.get('appearance', 'Not defined')}
- Typical clothing: {c.get('clothing', 'Not defined')}
- Resting expression: {c.get('expression', 'Not defined')}
- Voice quality: {c.get('voice', 'Not defined')}
- Emotional default: {c.get('emotion', 'Not defined')}""")
            else:
                char_context.append(f"CHARACTER: {speaker} - NO DEFINITION PROVIDED. Use voice inference.")

        # Location context
        loc = scene.get("location_hint", "unknown")
        loc_context = "LOCATION: Not defined"
        if loc in self._location_registry:
            l = self._location_registry[loc]
            loc_context = f"""LOCATION: {loc}
- Description: {l.get('description', 'Not defined')}
- Lighting: {l.get('lighting', 'Not defined')}
- Time of day: {l.get('time_of_day', 'Not defined')}
- Atmosphere: {l.get('atmosphere', 'Not defined')}"""

        # Dialogue
        dialogue_lines = []
        for d in scene.get("dialogue", []):
            dialogue_lines.append(f'[{d["start"]:.1f}s - {d["end"]:.1f}s] {d["speaker"]}: "{d["text"]}"')

        # Ambiguities
        ambiguity_note = ""
        if scene.get("ambiguity_flags"):
            ambiguity_note = f"\nNARRATIVE AMBIGUITIES: {', '.join(scene['ambiguity_flags'])}"

        return f"""{chr(10).join(char_context)}

{loc_context}

SCENE DIALOGUE:
{chr(10).join(dialogue_lines)}

Scene mood: {scene.get('mood', 'neutral')}
Duration: {scene.get('duration', 0):.1f}s
Suggested shots: {scene.get('suggested_shots', 3)}{ambiguity_note}

Generate the complete cinematic shot list as JSON."""

    def process_scene(self, scene: Dict) -> Dict:
        """Convert a single scene into cinematic shot specifications"""
        user_prompt = self._build_scene_prompt(scene)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_ctx": 8192,
                    "num_predict": 4096
                }
            )

            content = response["message"]["content"]

            # Extract JSON
            try:
                # Find JSON block
                start = content.index("{")
                end = content.rindex("}") + 1
                parsed = json.loads(content[start:end])
            except (ValueError, json.JSONDecodeError):
                # Try to clean up common LLM formatting issues
                cleaned = re.sub(r'```json\s*', '', content)
                cleaned = re.sub(r'```\s*', '', cleaned)
                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError:
                    print(f"[StoryEngine] WARNING: JSON parse failed for {scene['scene_id']}")
                    parsed = {
                        "shots": [],
                        "parse_error": True,
                        "raw_response": content[:500]
                    }

            return {
                "scene_id": scene["scene_id"],
                "start_time": scene["start_time"],
                "end_time": scene["end_time"],
                "speakers": scene["speakers"],
                "dialogue": scene["dialogue"],
                "cinematic_spec": parsed,
                "location_hint": scene.get("location_hint", "unknown"),
                "mood": scene.get("mood", "neutral")
            }

        except Exception as e:
            print(f"[StoryEngine] ERROR processing {scene['scene_id']}: {e}")
            return {
                "scene_id": scene["scene_id"],
                "error": str(e),
                "cinematic_spec": {"shots": []}
            }

    def process_all_scenes(self, scenes_path: Path, output_dir: Path):
        """Process all scenes from a scene file"""
        with open(scenes_path) as f:
            scenes = json.load(f)

        output_dir.mkdir(parents=True, exist_ok=True)

        for scene in scenes:
            print(f"[StoryEngine] Processing {scene['scene_id']}...")
            result = self.process_scene(scene)

            output_path = output_dir / f"{scene['scene_id']}.json"
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)

            shot_count = len(result.get("cinematic_spec", {}).get("shots", []))
            print(f"  -> {shot_count} shots generated")
