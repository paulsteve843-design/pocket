#!/usr/bin/env python3
"""
Audio Drama Cinema - Main Orchestrator
Handles multi-episode, multi-drama workflow with user interaction
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config_loader import ConfigManager
from core.multi_episode_manager import MultiEpisodeManager
from core.language_detector import LanguageDetector
from core.user_reference_integrator import UserReferenceIntegrator
from core.audio_processor import AudioProcessor

class DramaOrchestrator:
    def __init__(self):
        self.config = ConfigManager("config/system.yaml")
        self.manager = MultiEpisodeManager()
        self.language_detector = LanguageDetector()
        self.reference_integrator = UserReferenceIntegrator(self.config)

    def start_new_drama(self):
        """Initialize a new drama series"""
        print("\n" + "="*60)
        print("START NEW DRAMA SERIES")
        print("="*60)

        title = input("\nDrama title: ").strip()
        language = input("Language (en/ta/hi/te/ml/kn or 'auto'): ").strip() or "auto"
        theme = input("Theme (romance/thriller/horror/comedy/drama/action/mystery or 'auto'): ").strip() or "auto"

        drama_id = self.manager.create_drama(title, language, theme)
        print(f"\nCreated drama: {drama_id}")

        return drama_id

    def add_episode(self, drama_id: str):
        """Add a new episode to existing drama"""
        print(f"\n{'='*60}")
        print(f"ADD EPISODE TO {drama_id}")
        print(f"{'='*60}")

        # Find audio file
        input_dir = Path("assets/input")
        audio_files = list(input_dir.glob("*.mp3")) + list(input_dir.glob("*.wav")) +                       list(input_dir.glob("*.flac")) + list(input_dir.glob("*.m4a"))

        if not audio_files:
            print("No audio files in assets/input/")
            return

        print(f"\nAvailable audio files:")
        for i, f in enumerate(audio_files, 1):
            print(f"  {i}. {f.name}")

        choice = input("\nSelect file (number): ").strip()
        try:
            audio_file = audio_files[int(choice) - 1]
        except:
            audio_file = audio_files[0]

        ep_num = input(f"Episode number (auto={self.manager.list_episodes(drama_id).__len__() + 1}): ").strip()
        ep_num = int(ep_num) if ep_num.isdigit() else None

        episode_id = self.manager.add_episode(drama_id, audio_file, ep_num)
        print(f"\nAdded episode: {episode_id}")

        return episode_id

    def process_episode(self, drama_id: str, episode_id: str):
        """Process a single episode through the pipeline"""
        print(f"\n{'='*60}")
        print(f"PROCESSING {episode_id}")
        print(f"{'='*60}")

        drama_dir = self.manager.base_dir / drama_id
        episode_dir = drama_dir / "episodes" / episode_id

        with open(episode_dir / "state.json") as f:
            state = json.load(f)

        # Stage 1: Transcribe
        print(f"\n[1/7] Transcribing...")
        processor = AudioProcessor(self.config)
        transcript = processor.transcribe(Path(state["audio_path"]))

        # Auto-detect language and theme
        analysis = self.language_detector.analyze_drama(episode_dir / "transcript.json")
        print(f"  Detected language: {analysis['language_name']} ({analysis['language']})")
        print(f"  Detected theme: {analysis['theme']}")

        # Save transcript
        transcript_path = episode_dir / "transcript.json"
        processor.save_transcript(transcript, transcript_path)
        processor.unload_models()

        # Update state
        state["transcript_path"] = str(transcript_path)
        state["status"] = "transcribed"
        with open(episode_dir / "state.json", "w") as f:
            json.dump(state, f, indent=2)

        print(f"  Done! Transcript saved.")

        # Check if characters need to be defined
        registry = self.manager.get_character_registry(drama_id)
        speakers = transcript.get("unique_speakers", [])

        new_speakers = [s for s in speakers if s not in registry]
        if new_speakers:
            print(f"\n⚠️  New speakers detected: {', '.join(new_speakers)}")
            print("   Run 'python main.py --define-characters' to define them")
            return

        # Continue with remaining stages...
        print(f"\n✅ Episode {episode_id} transcribed. Run remaining stages with:")
        print(f"   python run_pipeline.py 2 (for episode {episode_id})")

    def define_characters_interactive(self, drama_id: str):
        """Interactive character definition with user references"""
        print(f"\n{'='*60}")
        print(f"DEFINE CHARACTERS FOR {drama_id}")
        print(f"{'='*60}")

        drama_dir = self.manager.base_dir / drama_id

        # Load transcript to get speakers
        episodes = self.manager.list_episodes(drama_id)
        if not episodes:
            print("No episodes found. Add an episode first.")
            return

        # Get latest transcript
        latest_ep = max(episodes, key=lambda e: e.get("episode_number", 0))
        transcript_path = Path(latest_ep.get("transcript_path", ""))

        if not transcript_path.exists():
            print("No transcript found. Process an episode first.")
            return

        with open(transcript_path) as f:
            transcript = json.load(f)

        registry = self.manager.get_character_registry(drama_id)
        speakers = transcript.get("unique_speakers", [])

        # Check for user-uploaded references
        user_uploads_dir = drama_dir / "characters" / "user_uploads"
        user_refs = list(user_uploads_dir.glob("*")) if user_uploads_dir.exists() else []

        if user_refs:
            print(f"\n📸 Found {len(user_refs)} user-uploaded reference image(s):")
            for ref in user_refs:
                print(f"   • {ref.name}")

        # Define each speaker
        new_chars = {}
        for speaker in speakers:
            if speaker in registry:
                print(f"\n✅ {speaker} already defined (appears in {registry[speaker].get('episode_count', 1)} episode(s))")
                continue

            print(f"\n{'─'*60}")
            print(f"NEW CHARACTER: {speaker}")
            print(f"{'─'*60}")

            # Check if user uploaded a reference for this speaker
            user_ref = None
            for ref in user_refs:
                if speaker.lower().replace("_", " ") in ref.stem.lower():
                    user_ref = ref
                    break

            if user_ref:
                print(f"\n📸 User reference found: {user_ref.name}")
                use_ref = input("Use this as primary reference? (y/n): ").strip().lower()
                if use_ref == 'y':
                    print("   Will use user photo as base for all generations.")

            # Get character details
            print(f"\nWhat is {speaker}'s role?")
            print("  1. Protagonist  2. Antagonist  3. Supporting  4. Narrator")
            role_choice = input("  Select: ").strip()
            roles = {"1": "protagonist", "2": "antagonist", "3": "supporting", "4": "narrator"}
            role = roles.get(role_choice, "supporting")

            if role == "narrator":
                char_data = {
                    "role": "narrator",
                    "age": "N/A", "gender": "N/A", "ethnicity": "N/A",
                    "appearance": "N/A - No visual",
                    "clothing": "N/A", "expression": "N/A",
                    "voice": "Narrator voiceover",
                    "emotion": "neutral",
                    "distinguishing": "No visual. Blue placeholder.",
                    "user_uploaded": False,
                    "reference_images": [],
                    "first_seen_episode": latest_ep.get("episode_number", 1),
                    "last_seen_episode": latest_ep.get("episode_number", 1),
                    "episode_count": 1
                }
            else:
                print(f"\nDescribe {speaker}'s appearance (be specific):")
                appearance = input("  Appearance: ").strip()

                clothing = input("  Clothing: ").strip()
                expression = input("  Resting expression: ").strip()
                voice = input("  Voice notes: ").strip()
                emotion = input("  Emotional default: ").strip()
                distinguishing = input("  Distinguishing features: ").strip()

                char_data = {
                    "role": role,
                    "age": input("  Age: ").strip(),
                    "gender": input("  Gender: ").strip(),
                    "ethnicity": input("  Ethnicity: ").strip(),
                    "appearance": appearance,
                    "clothing": clothing,
                    "expression": expression,
                    "voice": voice,
                    "emotion": emotion,
                    "distinguishing": distinguishing,
                    "user_uploaded": user_ref is not None,
                    "reference_images": [str(user_ref)] if user_ref else [],
                    "first_seen_episode": latest_ep.get("episode_number", 1),
                    "last_seen_episode": latest_ep.get("episode_number", 1),
                    "episode_count": 1
                }

            new_chars[speaker] = char_data
            print(f"\n✅ {speaker} defined!")

        # Update registry
        if new_chars:
            self.manager.update_character_registry(drama_id, new_chars)
            print(f"\n{'='*60}")
            print(f"SAVED {len(new_chars)} NEW CHARACTER(S)")
            print(f"{'='*60}")
        else:
            print(f"\nAll characters already defined.")

    def list_dramas(self):
        """List all dramas"""
        dramas = self.manager.list_dramas()
        print(f"\n{'='*60}")
        print("ALL DRAMAS")
        print(f"{'='*60}")

        for d in dramas:
            eps = self.manager.list_episodes(d["drama_id"])
            print(f"\n  {d['drama_id']}: {d['title']}")
            print(f"    Language: {d.get('language', 'auto')} | Theme: {d.get('theme', 'auto')}")
            print(f"    Episodes: {len(eps)} total")
            for ep in eps:
                print(f"      • {ep['episode_id']}: {ep['status']}")

    def run_menu(self):
        """Main menu"""
        while True:
            print(f"\n{'='*60}")
            print("AUDIO DRAMA CINEMA - MAIN MENU")
            print(f"{'='*60}")
            print("\n1. Start new drama series")
            print("2. Add episode to existing drama")
            print("3. Define characters for drama")
            print("4. Process episode (transcribe)")
            print("5. List all dramas")
            print("6. Run full pipeline for episode")
            print("0. Exit")

            choice = input("\nSelect: ").strip()

            if choice == "1":
                self.start_new_drama()
            elif choice == "2":
                dramas = self.manager.list_dramas()
                if not dramas:
                    print("No dramas found. Create one first.")
                    continue
                print("\nSelect drama:")
                for i, d in enumerate(dramas, 1):
                    print(f"  {i}. {d['title']} ({d['drama_id']})")
                d_choice = input("Number: ").strip()
                try:
                    drama_id = dramas[int(d_choice) - 1]["drama_id"]
                    self.add_episode(drama_id)
                except:
                    print("Invalid selection")
            elif choice == "3":
                dramas = self.manager.list_dramas()
                if not dramas:
                    print("No dramas found.")
                    continue
                print("\nSelect drama:")
                for i, d in enumerate(dramas, 1):
                    print(f"  {i}. {d['title']}")
                d_choice = input("Number: ").strip()
                try:
                    drama_id = dramas[int(d_choice) - 1]["drama_id"]
                    self.define_characters_interactive(drama_id)
                except:
                    print("Invalid selection")
            elif choice == "4":
                dramas = self.manager.list_dramas()
                if not dramas:
                    print("No dramas found.")
                    continue
                print("\nSelect drama:")
                for i, d in enumerate(dramas, 1):
                    print(f"  {i}. {d['title']}")
                d_choice = input("Number: ").strip()
                try:
                    drama_id = dramas[int(d_choice) - 1]["drama_id"]
                    episodes = self.manager.list_episodes(drama_id)
                    if not episodes:
                        print("No episodes found.")
                        continue
                    print("\nSelect episode:")
                    for i, ep in enumerate(episodes, 1):
                        print(f"  {i}. {ep['episode_id']} ({ep['status']})")
                    e_choice = input("Number: ").strip()
                    episode_id = episodes[int(e_choice) - 1]["episode_id"]
                    self.process_episode(drama_id, episode_id)
                except Exception as e:
                    print(f"Error: {e}")
            elif choice == "5":
                self.list_dramas()
            elif choice == "6":
                print("Run: python run_pipeline.py all")
            elif choice == "0":
                print("Goodbye!")
                break

if __name__ == "__main__":
    orchestrator = DramaOrchestrator()
    orchestrator.run_menu()
