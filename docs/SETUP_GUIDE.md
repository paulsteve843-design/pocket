# Audio Drama to Cinema Pipeline - Setup Guide

## Overview

This system converts audio dramas into cinematic video productions using local AI models. It runs entirely on your hardware with no cloud dependencies.

**Key Features:**
- Speech recognition with speaker diarization
- Automatic scene segmentation
- LLM-powered cinematic translation
- Character-consistent video generation
- Lip synchronization
- Blue-frame fallback for sensitive content (pipeline never stops)
- Narrator detection (skips visual generation, uses placeholder)

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | RTX 3060 (12GB VRAM) | RTX 4090 (24GB VRAM) |
| RAM | 16GB | 32GB |
| Storage | 50GB free | 100GB+ free (models + outputs) |
| OS | Windows 10/11, Linux | Linux (Ubuntu 22.04) |

**Your RTX 3060 + 16GB RAM setup will work.** Generation will be slower but fully functional.

---

## Step-by-Step Installation

### Step 1: Install Prerequisites

**Windows:**
```bash
# Install Python 3.10 from python.org
# Install Git from git-scm.com
# Install FFmpeg from ffmpeg.org (add to PATH)
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip git ffmpeg
```

### Step 2: Create Project Directory

Extract the ZIP file to your desired location:
```bash
cd C:\Projects        # Windows
cd ~/projects          # Linux

# Extract audio_drama_cinema.zip here
# You should have:
# audio_drama_cinema/
#   ├── src/
#   ├── config/
#   ├── assets/
#   ├── output/
#   ├── models/
#   ├── docs/
#   ├── run_pipeline.py
#   ├── requirements.txt
#   └── setup.py
```

### Step 3: Create Python Environment

```bash
cd audio_drama_cinema

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# You should see (venv) in your prompt
```

### Step 4: Install PyTorch (CUDA 11.8)

```bash
pip install torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1+cu118     --index-url https://download.pytorch.org/whl/cu118
```

Verify installation:
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}')"
```

You should see your RTX 3060 listed.

### Step 5: Install Remaining Dependencies

```bash
pip install -r requirements.txt
```

This will take 10-20 minutes. Large models will download automatically on first use.

### Step 6: Install Ollama (for Local LLM)

**Windows:**
1. Download from https://ollama.com
2. Run the installer
3. Ollama runs as a background service

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Pull the language model:**
```bash
ollama pull qwen2.5:7b
```

This downloads ~4GB. Verify:
```bash
ollama list
# Should show: qwen2.5:7b
```

### Step 7: Verify FFmpeg

```bash
ffmpeg -version
# Should show version info
```

If not found, add FFmpeg to your system PATH.

---

## Configuration

### Edit config/system.yaml

Open `config/system.yaml` and adjust for your system:

```yaml
hardware:
  device: cuda
  max_vram_gb: 11        # Leave 1GB headroom on RTX 3060
  max_ram_gb: 14         # Leave 2GB for OS
  enable_cpu_offload: true   # Essential for RTX 3060
```

### Define Your Characters

Open `assets/characters.json` and replace the template with your actual characters.

**Important fields:**
- `role`: `protagonist`, `antagonist`, `supporting`, or `narrator`
- `appearance`: Detailed visual description (age, ethnicity, hair, eyes, build, distinguishing features)
- `clothing`: What they typically wear
- `expression`: Resting face, emotional default
- `voice`: How voice suggests their appearance

**Narrator handling:** Set `role` to `narrator` and the system will automatically skip visual generation, using blue placeholder frames instead. The audio continues uninterrupted.

### Define Your Locations

Open `assets/locations.json` and describe each setting:
- `description`: Detailed visual description
- `lighting`: Key light sources, mood
- `time_of_day`: When scenes typically occur here
- `atmosphere`: Emotional tone of the space

### Define Props (Optional)

Open `assets/props.json` for objects that appear across scenes. The system tracks their state to maintain continuity.

---

## Running the Pipeline

### Method 1: Stage by Stage (Recommended for first run)

```bash
# Stage 1: Transcription
python run_pipeline.py 1

# Review output/transcripts/ - check speaker detection accuracy

# Stage 2: Scene Segmentation
python run_pipeline.py 2

# Review output/scenes/ - check scene boundaries

# Stage 3: Story Understanding
python run_pipeline.py 3

# Review output/prompts/ - check cinematic translations

# Stage 4: Reference Images
python run_pipeline.py 4

# Review assets/refs/ - if characters look wrong, edit descriptions and rerun

# Stage 5: Video Generation
python run_pipeline.py 5

# Stage 6: Lip Sync & Enhancement
python run_pipeline.py 6

# Stage 7: Final Assembly
python run_pipeline.py 7
```

### Method 2: Full Pipeline

```bash
python run_pipeline.py all
```

This runs all stages unattended. Stops if any stage fails.

---

## Understanding the Fallback System

### Blue Frame Fallback

If video generation fails 10 times for any shot (content sensitivity, OOM, model refusal), the system automatically generates a **cinematic blue placeholder frame** instead of crashing.

- Audio continues uninterrupted
- Pipeline never stops
- You can identify blue frames in the final output
- Replace them later by rerunning specific shots

### Narrator Handling

Characters with `role: "narrator"` automatically skip visual generation. The system uses blue frames with the narrator's scene description as text overlay. This is intentional - narrators typically provide voiceover without appearing on screen.

---

## Performance Expectations (RTX 3060)

| Stage | Time per Unit | Notes |
|-------|---------------|-------|
| Transcription | 0.3x realtime | 10 min audio = 3 min processing |
| Segmentation | Instant | Rule-based |
| Story Understanding | 5-15s/scene | LLM inference |
| Reference Images | 30-60s/image | FLUX.1-schnell |
| Video Clips | 2-4 min/clip | LTX-Video (main bottleneck) |
| Lip Sync | 30-60s/clip | Wav2Lip or fallback |
| Enhancement | 1-2 min/clip | Upscaling + interpolation |

**Example: 10-minute audio drama with 15 scenes, ~45 shots**
- Total processing: 4-6 hours (mostly unattended)
- VRAM usage peaks at ~10GB during video generation

---

## Troubleshooting

### Out of Memory During Video Generation

1. Reduce resolution in `config/system.yaml`:
   ```yaml
   video:
     resolution: [384, 256]  # Instead of [512, 320]
   ```

2. Enable more aggressive CPU offloading:
   ```yaml
   hardware:
     enable_cpu_offload: true
   ```

3. Reduce frame count:
   ```yaml
   video:
     num_frames: 17  # Instead of 25
   ```

### Model Download Fails

Models download automatically on first use. If interrupted:
```bash
# Clear cache and retry
rm -rf ~/.cache/huggingface/
rm -rf ~/.cache/torch/
```

### Ollama Connection Error

Ensure Ollama is running:
```bash
# Windows: Check system tray icon
# Linux:
sudo systemctl status ollama
sudo systemctl start ollama
```

### FFmpeg Not Found

Windows: Add FFmpeg `bin` folder to system PATH.
Linux: `sudo apt install ffmpeg`

### Blue Frames Everywhere

This means video generation is failing consistently. Check:
1. VRAM available: `nvidia-smi`
2. Model loaded correctly
3. Try reducing resolution in config

---

## Output Structure

```
output/
├── transcripts/          # Whisper output with speaker IDs
│   └── my_drama.json
├── scenes/               # Scene breakdown
│   └── my_drama_scenes.json
├── prompts/              # LLM cinematic specifications
│   └── my_drama_sc0001.json
├── clips/                # Raw video clips
│   └── my_drama_sc0001_s000.mp4
├── lipsync/              # Processed clips
│   └── my_drama_sc0001_s000_final.mp4
├── final_movie.mp4       # Ungraded final
└── final_movie_graded.mp4 # Color graded final

assets/
├── input/                # Your audio files
├── characters.json       # Character definitions
├── locations.json        # Location definitions
├── props.json            # Prop tracking
└── refs/                 # Generated reference images
    ├── character_sarah.png
    └── location_interior_apartment.png
```

---

## Next Steps After First Run

1. **Review the final video** - Note which shots need improvement
2. **Iterate on character descriptions** - Better descriptions = better consistency
3. **Adjust cinematic prompts** - Edit output/prompts/ files manually if needed
4. **Rerun specific stages** - No need to start from scratch
5. **Experiment with styles** - Change color grade, lighting moods in config

---

## Advanced: Customizing the Pipeline

### Adding New Shot Types

Edit `src/core/story_engine.py` - modify the `CINEMATIC_SYSTEM_PROMPT` to include new shot grammar rules.

### Changing Visual Style

Edit `config/system.yaml`:
```yaml
pipeline:
  video:
    guidance_scale: 5.0  # Higher = more literal prompt following
    num_inference_steps: 50  # Higher = better quality, slower
```

### Training Character LoRAs

For extreme consistency, train a LoRA per character on the generated reference images. This is advanced and requires additional tools.

---

## Support

- Check `output/pipeline.log` for detailed error messages
- Review individual stage outputs before proceeding
- The pipeline is modular - each stage can be rerun independently
