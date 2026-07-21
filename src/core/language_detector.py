"""
Language Detection & Whisper Model Selection
Auto-detects language and loads appropriate Whisper model
"""
import json
from pathlib import Path
from typing import Dict, Optional

class LanguageDetector:
    """Detects language from audio and maps to appropriate models"""

    # Whisper model mapping by language
    WHISPER_MODELS = {
        "en": {
            "model": "openai/whisper-medium",
            "align_model": "en",
            "diarization": "pyannote/speaker-diarization-3.1"
        },
        "ta": {
            "model": "openai/whisper-medium",  # Whisper handles Tamil
            "align_model": "ta",
            "diarization": "pyannote/speaker-diarization-3.1"
        },
        "hi": {
            "model": "openai/whisper-medium",
            "align_model": "hi",
            "diarization": "pyannote/speaker-diarization-3.1"
        },
        "te": {
            "model": "openai/whisper-medium",
            "align_model": "te",
            "diarization": "pyannote/speaker-diarization-3.1"
        },
        "ml": {
            "model": "openai/whisper-medium",
            "align_model": "ml",
            "diarization": "pyannote/speaker-diarization-3.1"
        },
        "kn": {
            "model": "openai/whisper-medium",
            "align_model": "kn",
            "diarization": "pyannote/speaker-diarization-3.1"
        }
    }

    # LLM prompt templates by language
    PROMPT_TEMPLATES = {
        "en": {
            "system_prompt": "You are a cinematographer...",
            "shot_types": ["close_up", "medium_shot", "wide_shot", "over_shoulder", "insert"],
            "moods": ["tense", "romantic", "suspense", "action", "melancholy", "mysterious"]
        },
        "ta": {
            "system_prompt": "நீங்கள் ஒரு திரைப்பட இயக்குநர்...",  # Tamil
            "shot_types": ["நெருக்கமான", "நடுத்தர", "பரந்த", "தோள்_மீது", "செருகல்"],
            "moods": ["பதட்டம்", "காதல்", "சந்தேகம்", "செயல்", "சோகம்", "மர்மம்"]
        },
        "hi": {
            "system_prompt": "आप एक सिनेमैटोग्राफर हैं...",  # Hindi
            "shot_types": ["क्लोज_अप", "मीडियम", "वाइड", "ओवर_शोल्डर", "इंसर्ट"],
            "moods": ["तनाव", "रोमांस", "संदेह", "एक्शन", "उदासी", "रहस्य"]
        }
    }

    # Theme detection keywords
    THEME_KEYWORDS = {
        "romance": ["love", "kiss", "heart", "together", "அன்பு", "காதல்", "प्यार", "दिल"],
        "thriller": ["run", "chase", "danger", "secret", "அபாயம்", "ரகசியம்", "खतरा", "रहस्य"],
        "horror": ["scream", "blood", "dark", "ghost", "பயம்", "இரத்தம்", "डर", "खून"],
        "comedy": ["laugh", "funny", "joke", "smile", "சிரிப்பு", "காமெடி", "हंसी", "मज़ाक"],
        "drama": ["family", "emotional", "conflict", "relationship", "குடும்பம்", "உணர்வு", "परिवार", "भावना"],
        "action": ["fight", "explosion", "gun", "punch", "சண்டை", "துப்பாக்கி", "लड़ाई", "बंदूक"],
        "mystery": ["clue", "detective", "murder", "investigate", "குற்றவியல்", "விசாரணை", "जासूस", "हत्या"]
    }

    def detect_language(self, transcript_text: str) -> str:
        """Detect language from transcript text"""
        # Simple detection based on character ranges and keywords
        text_sample = transcript_text[:1000].lower()

        # Tamil detection (Unicode range)
        tamil_chars = sum(1 for c in text_sample if '஀' <= c <= '௿')
        if tamil_chars > 10:
            return "ta"

        # Hindi detection
        hindi_chars = sum(1 for c in text_sample if 'ऀ' <= c <= 'ॿ')
        if hindi_chars > 10:
            return "hi"

        # Telugu
        telugu_chars = sum(1 for c in text_sample if 'ఀ' <= c <= '౿')
        if telugu_chars > 10:
            return "te"

        # Malayalam
        malayalam_chars = sum(1 for c in text_sample if 'ഀ' <= c <= 'ൿ')
        if malayalam_chars > 10:
            return "ml"

        # Kannada
        kannada_chars = sum(1 for c in text_sample if 'ಀ' <= c <= '೿')
        if kannada_chars > 10:
            return "kn"

        # Default to English
        return "en"

    def detect_theme(self, transcript_text: str) -> str:
        """Detect theme/genre from transcript content"""
        text_lower = transcript_text.lower()
        scores = {}

        for theme, keywords in self.THEME_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[theme] = score

        best_theme = max(scores, key=scores.get)
        return best_theme if scores[best_theme] > 0 else "drama"

    def get_whisper_config(self, language: str) -> Dict:
        """Get Whisper model configuration for detected language"""
        return self.WHISPER_MODELS.get(language, self.WHISPER_MODELS["en"])

    def get_llm_prompt_template(self, language: str) -> Dict:
        """Get LLM prompt template for detected language"""
        return self.PROMPT_TEMPLATES.get(language, self.PROMPT_TEMPLATES["en"])

    def get_color_palette(self, theme: str) -> Dict:
        """Get color grading palette for detected theme"""
        palettes = {
            "romance": {"primary": "warm_amber", "secondary": "soft_pink", "contrast": "low"},
            "thriller": {"primary": "cool_blue", "secondary": "desaturated", "contrast": "high"},
            "horror": {"primary": "desaturated", "secondary": "green_tint", "contrast": "extreme"},
            "comedy": {"primary": "bright_warm", "secondary": "saturated", "contrast": "medium"},
            "drama": {"primary": "neutral", "secondary": "warm", "contrast": "medium_high"},
            "action": {"primary": "cool", "secondary": "orange_teal", "contrast": "high"},
            "mystery": {"primary": "blue_green", "secondary": "desaturated", "contrast": "high"}
        }
        return palettes.get(theme, palettes["drama"])

    def analyze_drama(self, transcript_path: Path) -> Dict:
        """Full analysis: language, theme, recommendations"""
        with open(transcript_path) as f:
            data = json.load(f)

        # Combine all dialogue text
        all_text = " ".join([seg.get("text", "") for seg in data.get("segments", [])])

        language = self.detect_language(all_text)
        theme = self.detect_theme(all_text)

        return {
            "language": language,
            "language_name": self._get_language_name(language),
            "theme": theme,
            "whisper_config": self.get_whisper_config(language),
            "prompt_template": self.get_llm_prompt_template(language),
            "color_palette": self.get_color_palette(theme),
            "confidence": "high" if len(all_text) > 500 else "medium"
        }

    def _get_language_name(self, code: str) -> str:
        names = {
            "en": "English", "ta": "Tamil", "hi": "Hindi",
            "te": "Telugu", "ml": "Malayalam", "kn": "Kannada"
        }
        return names.get(code, code)
