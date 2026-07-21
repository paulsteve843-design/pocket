"""
Audio ingestion, transcription, and speaker diarization
Optimized for RTX 3060 with batch processing
"""
import json
import os
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import whisper
from whisperx import load_align_model, align
from whisperx.diarize import DiarizationPipeline
import soundfile as sf

class AudioProcessor:
    def __init__(self, config):
        self.config = config
        self.device = config.get_device()
        self.whisper_model = None
        self.align_model = None
        self.align_metadata = None
        self.diarize_model = None
        self._loaded = False

    def load_models(self):
        if self._loaded:
            return

        print("[AudioProcessor] Loading Whisper model...")
        self.whisper_model = whisper.load_model(
            "medium",
            device=self.device,
            download_root=str(self.config.get_path("models"))
        )

        print("[AudioProcessor] Loading alignment model...")
        self.align_model, self.align_metadata = load_align_model(
            "en", device=self.device
        )

        print("[AudioProcessor] Loading diarization model...")
        # pyannote/speaker-diarization-3.1 (and the segmentation model it
        # depends on) are gated on HuggingFace Hub. Without an access token
        # this fails even with correct hardware. Get one for free at
        # https://huggingface.co/settings/tokens after accepting the terms
        # at https://huggingface.co/pyannote/speaker-diarization-3.1 and
        # https://huggingface.co/pyannote/segmentation-3.0, then set it as
        # the HF_TOKEN environment variable before running the pipeline.
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        if not hf_token:
            raise RuntimeError(
                "HF_TOKEN environment variable not set. pyannote/speaker-diarization-3.1 "
                "is a gated model on HuggingFace: accept its terms (and "
                "pyannote/segmentation-3.0's terms) at huggingface.co, create an access "
                "token at https://huggingface.co/settings/tokens, and set it via "
                "'set HF_TOKEN=your_token' (Windows cmd) or '$env:HF_TOKEN=\"your_token\"' "
                "(PowerShell) before running the pipeline."
            )
        self.diarize_model = DiarizationPipeline(
            model_name=self.config.models.diarization_model,
            token=hf_token,
            device=self.device
        )

        self._loaded = True
        print("[AudioProcessor] All models loaded")

    def unload_models(self):
        """Free VRAM between stages"""
        if self.whisper_model:
            del self.whisper_model
            self.whisper_model = None
        if self.align_model:
            del self.align_model
            self.align_model = None
        if self.diarize_model:
            del self.diarize_model
            self.diarize_model = None
        torch.cuda.empty_cache()
        self._loaded = False

    def transcribe(self, audio_path: Path) -> Dict:
        self.load_models()

        print(f"[AudioProcessor] Transcribing {audio_path.name}...")

        # Whisper base transcription
        result = self.whisper_model.transcribe(
            str(audio_path),
            language="en",
            word_timestamps=True,
            fp16=(self.device.type == "cuda")
        )

        # WhisperX alignment for precise word timestamps
        print("[AudioProcessor] Aligning word timestamps...")
        result_aligned = align(
            result["segments"],
            self.align_model,
            self.align_metadata,
            str(audio_path),
            self.device
        )

        # Speaker diarization
        print("[AudioProcessor] Identifying speakers...")
        diarize_segments = self.diarize_model(str(audio_path))

        # Merge diarization with transcription
        structured = self._merge_speakers(result_aligned, diarize_segments)

        # Add audio metadata
        audio_info = sf.info(str(audio_path))
        structured["audio_meta"] = {
            "duration": audio_info.duration,
            "sample_rate": audio_info.samplerate,
            "channels": audio_info.channels
        }

        return structured

    def _merge_speakers(self, transcript: Dict, diarize_segments) -> Dict:
        speaker_map = {}
        for seg in diarize_segments.itertracks(yield_label=True):
            start, end, speaker = seg[0].start, seg[0].end, seg[2]
            speaker_map[(start, end)] = speaker

        def get_speaker(start: float, end: float) -> str:
            best_speaker = "UNKNOWN"
            best_overlap = 0
            for (s, e), spk in speaker_map.items():
                overlap = max(0, min(end, e) - max(start, s))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = spk
            return best_speaker

        output = {
            "source": str(transcript.get("source", "")),
            "language": transcript.get("language", "en"),
            "duration": 0.0,
            "segments": []
        }

        for seg in transcript["segments"]:
            words = []
            for w in seg.get("words", []):
                if isinstance(w, dict):
                    words.append({
                        "text": w.get("word", ""),
                        "start": w.get("start", 0),
                        "end": w.get("end", 0),
                        "speaker": get_speaker(w.get("start", 0), w.get("end", 0)),
                        "confidence": w.get("score", 1.0)
                    })

            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)

            segment = {
                "id": seg.get("id", 0),
                "start": seg_start,
                "end": seg_end,
                "text": seg.get("text", ""),
                "speaker": get_speaker(seg_start, seg_end),
                "words": words,
                "confidence": seg.get("avg_logprob", 0)
            }

            output["segments"].append(segment)
            output["duration"] = max(output["duration"], seg_end)

        # Build speaker summary
        speakers = {}
        for seg in output["segments"]:
            spk = seg["speaker"]
            if spk not in speakers:
                speakers[spk] = {"segments": 0, "words": 0, "duration": 0}
            speakers[spk]["segments"] += 1
            speakers[spk]["words"] += len(seg["words"])
            speakers[spk]["duration"] += seg["end"] - seg["start"]

        output["speaker_summary"] = speakers
        output["unique_speakers"] = list(speakers.keys())

        return output

    def save_transcript(self, transcript: Dict, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(transcript, f, indent=2)
        print(f"[AudioProcessor] Saved transcript: {output_path}")
