#!/usr/bin/env python3
"""
Interactive Audio Drama Setup
1. Transcribes audio
2. Detects speakers
3. Asks you about each speaker with visual references
4. Infers locations
5. Generates characters.json and locations.json automatically
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config_loader import ConfigManager
from core.audio_processor import AudioProcessor
from core.scene_segmenter import SceneSegmenter

class InteractiveSetup:
    def __init__(self):
        self.config = ConfigManager("config/system.yaml")
        self.audio_file = None
        self.transcript = None
        self.speakers = {}
        self.locations = {}

    def find_audio(self):
        """Find audio files in assets/input/"""
        input_dir = Path("assets/input")
        audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3")) +                       list(input_dir.glob("*.flac")) + list(input_dir.glob("*.m4a"))

        if not audio_files:
            print("No audio files found in assets/input/")
            print("Please copy your audio drama file there first.")
            return None

        print(f"Found {len(audio_files)} audio file(s):")
        for i, f in enumerate(audio_files, 1):
            print(f"  {i}. {f.name}")

        if len(audio_files) == 1:
            return audio_files[0]

        choice = input("Select file number: ").strip()
        try:
            return audio_files[int(choice) - 1]
        except:
            return audio_files[0]

    def transcribe(self, audio_file):
        """Transcribe audio and detect speakers"""
        print(f"
{'='*60}")
        print("STEP 1: TRANSCRIBING AUDIO")
        print(f"{'='*60}")

        processor = AudioProcessor(self.config)
        transcript = processor.transcribe(audio_file)

        output_dir = Path("output/transcripts")
        output_dir.mkdir(parents=True, exist_ok=True)
        processor.save_transcript(transcript, output_dir / f"{audio_file.stem}.json")
        processor.unload_models()

        print(f"
Transcription complete!")
        print(f"  Duration: {transcript.get('duration', 0):.1f}s")
        print(f"  Speakers detected: {len(transcript.get('unique_speakers', []))}")

        return transcript

    def ask_speaker_details(self, speaker_id, sample_dialogue):
        """Interactive questionnaire for each speaker"""
        print(f"
{'='*60}")
        print(f"SPEAKER: {speaker_id}")
        print(f"{'='*60}")

        print(f"
Sample dialogue:")
        sample = sample_dialogue[:200] + "..." if len(sample_dialogue) > 200 else sample_dialogue
        print(f'  "{sample}"')

        print(f"
What is this speaker's role?")
        print("  1. Protagonist (main hero)")
        print("  2. Antagonist (villain/opposition)")
        print("  3. Supporting (side character)")
        print("  4. Narrator (voiceover only, no visual)")
        print("  5. Other / Unknown")

        role_choice = input("  Select (1-5): ").strip()
        roles = {"1": "protagonist", "2": "antagonist", "3": "supporting", 
                 "4": "narrator", "5": "supporting"}
        role = roles.get(role_choice, "supporting")

        if role == "narrator":
            print("
Narrator detected - will use voiceover only, no visual generation.")
            return {
                "role": "narrator",
                "age": "N/A",
                "gender": "N/A",
                "ethnicity": "N/A",
                "appearance": "N/A - No visual representation needed",
                "clothing": "N/A",
                "expression": "N/A",
                "voice": "Narrator voice - provides context and scene transitions",
                "emotion": "neutral",
                "distinguishing": "No visual. Voice only. Blue placeholder frames will be used."
            }

        print(f"
Let's define this character's visual appearance.")

        age = input("
  Age (approximate): ").strip()
        gender = input("  Gender (male/female/non-binary): ").strip().lower()
        ethnicity = input("  Ethnicity / Heritage: ").strip()

        print(f"
  PHYSICAL APPEARANCE")
        print("  Describe: build, face, hair, eyes, skin, marks, scars")
        print("  Archetypes: 'false weakling', 'supreme wastrel', 'ruined beauty', 'predatory charm'")
        appearance = input("  Appearance: ").strip()

        print(f"
  CLOTHING & STYLE")
        clothing = input("  What do they wear? ").strip()

        print(f"
  RESTING EXPRESSION (face when no one watches)")
        expression = input("  Expression: ").strip()

        print(f"
  VOICE-TO-VISUAL (how voice suggests physical presence)")
        voice = input("  Voice notes: ").strip()

        print(f"
  EMOTIONAL DEFAULT")
        emotion = input("  Baseline emotion: ").strip()

        distinguishing = input("
  DISTINGUISHING FEATURES: ").strip()

        return {
            "role": role,
            "age": age,
            "gender": gender,
            "ethnicity": ethnicity,
            "appearance": appearance,
            "clothing": clothing,
            "expression": expression,
            "voice": voice,
            "emotion": emotion,
            "distinguishing": distinguishing
        }

    def process_speakers(self, transcript):
        """Process all detected speakers"""
        print(f"
{'='*60}")
        print("STEP 2: CHARACTER DEFINITION")
        print(f"{'='*60}")

        speakers_data = {}
        segments = transcript.get("segments", [])

        for speaker_id in transcript.get("unique_speakers", []):
            sample = ""
            for seg in segments:
                if seg.get("speaker") == speaker_id and len(sample) < 300:
                    sample += seg.get("text", "") + " "

            char_data = self.ask_speaker_details(speaker_id, sample.strip())
            speakers_data[speaker_id] = char_data
            print(f"
  Character '{speaker_id}' defined!")

        return speakers_data

    def infer_locations(self, transcript):
        """Infer locations from audio content"""
        print(f"
{'='*60}")
        print("STEP 3: LOCATION INFERENCE")
        print(f"{'='*60}")

        segmenter = SceneSegmenter(self.config)
        temp_path = Path("output/temp_transcript.json")
        with open(temp_path, "w") as f:
            json.dump(transcript, f)

        scenes = segmenter.process(temp_path)

        locations_found = {}
        for scene in scenes:
            loc = scene.location_hint
            if loc not in locations_found:
                locations_found[loc] = scene

        print(f"
Inferred {len(locations_found)} location(s):")
        locations_data = {}

        for loc_name, scene in locations_found.items():
            print(f"
  Location: {loc_name}")
            if scene.dialogue:
                print(f"  From: {scene.dialogue[0]['text'][:100]}...")

            description = input("  Visual description: ").strip()
            lighting = input("  Lighting: ").strip()
            time = input("  Time of day (day/night/variable): ").strip()
            atmosphere = input("  Atmosphere/mood: ").strip()

            locations_data[loc_name] = {
                "type": loc_name,
                "description": description,
                "lighting": lighting,
                "time_of_day": time,
                "atmosphere": atmosphere
            }
            print(f"  Location '{loc_name}' defined!")

        return locations_data

    def save_definitions(self, speakers_data, locations_data):
        """Save generated JSON files"""
        print(f"
{'='*60}")
        print("STEP 4: SAVING DEFINITIONS")
        print(f"{'='*60}")

        char_path = Path("assets/characters.json")
        with open(char_path, "w") as f:
            json.dump(speakers_data, f, indent=2)
        print(f"Saved {len(speakers_data)} characters to {char_path}")

        loc_path = Path("assets/locations.json")
        with open(loc_path, "w") as f:
            json.dump(locations_data, f, indent=2)
        print(f"Saved {len(locations_data)} locations to {loc_path}")

        print(f"
{'='*60}")
        print("SETUP COMPLETE")
        print(f"{'='*60}")
        print(f"
Characters:")
        for name, data in speakers_data.items():
            role = data.get("role", "unknown")
            note = " (NARRATOR)" if role == "narrator" else ""
            print(f"  - {name}: {role}{note}")

        print(f"
Locations:")
        for name in locations_data:
            print(f"  - {name}")

        print(f"
Next: python run_pipeline.py 1")

    def run(self):
        """Main entry point"""
        print(f"{'='*60}")
        print("AUDIO DRAMA - INTERACTIVE SETUP")
        print(f"{'='*60}")
        print("
This will:")
        print("  1. Transcribe your audio drama")
        print("  2. Detect all speakers")
        print("  3. Ask you about each character")
        print("  4. Infer locations from audio")
        print("  5. Generate characters.json and locations.json")

        input("
Press Enter to start...")

        audio_file = self.find_audio()
        if not audio_file:
            return

        self.transcript = self.transcribe(audio_file)
        speakers_data = self.process_speakers(self.transcript)
        locations_data = self.infer_locations(self.transcript)
        self.save_definitions(speakers_data, locations_data)

if __name__ == "__main__":
    setup = InteractiveSetup()
    setup.run()
