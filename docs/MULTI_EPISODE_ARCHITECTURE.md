# Multi-Episode Audio Drama Cinema Pipeline
# Supports: Multiple dramas, multiple episodes, character persistence, user references

project/
├── dramas/                          # Each drama gets its own folder
│   ├── drama_001_tamil_romance/     # Example: Tamil romance drama
│   │   ├── metadata.json            # Drama title, language, theme, total episodes
│   │   ├── characters/              # Character definitions + reference images
│   │   │   ├── character_registry.json
│   │   │   ├── refs/                 # User-uploaded + AI-generated reference images
│   │   │   │   ├── sarah_face_ep01.png
│   │   │   │   ├── sarah_face_ep05.png  # Updated across episodes
│   │   │   │   └── marcus_face.png
│   │   │   └── user_uploads/         # User-provided reference photos
│   │   │       ├── sarah_reference.jpg
│   │   │       └── location_apartment.jpg
│   │   ├── locations/               # Location definitions + reference images
│   │   │   ├── location_registry.json
│   │   │   └── refs/
│   │   ├── episodes/                # All episodes for this drama
│   │   │   ├── ep_001/
│   │   │   │   ├── audio.mp3
│   │   │   │   ├── transcript.json
│   │   │   │   ├── scenes.json
│   │   │   │   ├── prompts.json
│   │   │   │   ├── clips/
│   │   │   │   └── final_ep001.mp4
│   │   │   ├── ep_002/
│   │   │   │   ├── audio.mp3
│   │   │   │   ├── transcript.json
│   │   │   │   └── ...
│   │   │   └── ep_030/
│   │   └── continuity_state.json    # Tracks character aging, prop states, timeline
│   │
│   └── drama_002_english_thriller/    # Another drama, different theme
│       ├── metadata.json
│       ├── characters/
│       ├── locations/
│       └── episodes/
│
├── shared/                          # Cross-drama shared assets
│   ├── models/                      # Downloaded AI models (shared)
│   └── themes/                      # Theme presets (noir, romance, horror, etc.)
│
└── src/
    ├── core/
    │   ├── multi_episode_manager.py    # NEW: Manages drama/episode lifecycle
    │   ├── character_memory.py         # NEW: Persistent character identity across episodes
    │   ├── language_detector.py        # NEW: Auto-detect language, load appropriate Whisper model
    │   ├── theme_analyzer.py           # NEW: Detect genre/theme from audio content
    │   ├── user_reference_integrator.py # NEW: Blend user photos with AI generation
    │   └── episode_continuity.py       # NEW: Track state changes across episodes
    │
    └── stages/
        ├── stage_00_drama_init.py      # NEW: Initialize new drama, detect language/theme
        ├── stage_01_transcribe.py      # Modified: Multi-language support
        ├── stage_02_segment.py         # Modified: Theme-aware segmentation
        ├── stage_03_understand.py      # Modified: Episode-aware story understanding
        ├── stage_04_generate_refs.py   # Modified: User reference integration
        ├── stage_05_generate_video.py  # Modified: Theme-consistent generation
        ├── stage_06_lipsync.py
        └── stage_07_assemble.py
