"""
Resolves input/output paths for each pipeline stage.

Why this exists:
The original stages always read/wrote a single global folder
(assets/input, output/transcripts, ...). That works for one person
running the CLI once, but it means the web studio can't process more
than one drama/episode independently -- every run reads and writes the
same files, so nothing looks "dynamic" per drama.

This module lets each stage resolve paths in priority order:
  1. PIPELINE_EPISODE_DIR (per-episode data: audio, transcripts, scenes,
     prompts, clips, lipsync, final video)
  2. PIPELINE_DRAMA_DIR (per-drama data that spans episodes: characters,
     locations, props, reference images)
  3. The original global legacy path (so plain `python run_pipeline.py all`
     still works exactly like before if you're not using the web studio)
"""
import os
from pathlib import Path


def get_drama_dir():
    v = os.environ.get("PIPELINE_DRAMA_DIR")
    return Path(v) if v else None


def get_episode_dir():
    v = os.environ.get("PIPELINE_EPISODE_DIR")
    return Path(v) if v else None


def episode_path(relative, legacy):
    """Path that lives under the current episode (audio, transcripts, scenes,
    prompts, clips, lipsync, final video). Falls back to the legacy global
    path when no episode context is set."""
    ep = get_episode_dir()
    if ep:
        return ep / relative
    return Path(legacy)


def drama_path(relative, legacy):
    """Path that lives under the current drama and spans episodes
    (characters.json, locations.json, props.json, refs/). Falls back to the
    legacy global path when no drama context is set."""
    dr = get_drama_dir()
    if dr:
        return dr / relative
    return Path(legacy)


def is_scoped():
    """True when running inside the web studio's per-drama/episode context."""
    return get_drama_dir() is not None or get_episode_dir() is not None
