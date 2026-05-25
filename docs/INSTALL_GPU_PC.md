# GPU PC install guide — Linux

End-to-end setup for the open-source video-generation rig that renders Shorts from the aircraft database. Tested target: **Ubuntu 22.04 / 24.04 LTS** on an RTX 4090 (24 GB VRAM).

This guide takes you from a fresh Linux install to **`python video_pipeline/render_today.py`** producing 4 vertical Shorts per day.

> 💡 **Time budget:** ~3-4 hours total, mostly waiting for model downloads. Allocate one evening.

---

## Step 0 — Hardware checklist

| Component | Minimum | Recommended |
|---|---|---|
| GPU | RTX 3090 (24 GB) | RTX 4090 (24 GB) or better |
| CPU | 8-core | 12-core+ |
| RAM | 32 GB | 64 GB |
| Disk | 500 GB NVMe | 1 TB NVMe |
| Network | 100 Mbps | gigabit (large model downloads) |
| OS | Ubuntu 22.04 | Ubuntu 24.04 LTS |

You will download ~80-150 GB of model weights.

---

## Step 1 — System packages

```bash
sudo apt update && sudo apt upgrade -y

# Build tools + ffmpeg + git + LFS (large model weights)
sudo apt install -y build-essential git git-lfs curl wget \
    ffmpeg libsndfile1 \
    libgl1 libglib2.0-0 \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    pkg-config

git lfs install
```

Verify ffmpeg can write H.264:

```bash
ffmpeg -encoders 2>&1 | grep -E 'libx264|aac'
# expect:  V..... libx264   and   A..... aac
```

---

## Step 2 — NVIDIA driver + CUDA 12.x

```bash
# Driver — pick the recommended version
sudo ubuntu-drivers autoinstall
sudo reboot
```

After reboot, confirm:

```bash
nvidia-smi
# should show your GPU + a Driver Version: 545.xx or newer
```

Install CUDA Toolkit 12.4 (newer toolkits work with older drivers):

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-4

# Add to PATH (one-time)
echo 'export PATH=/usr/local/cuda-12.4/bin:$PATH'              >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

nvcc --version  # confirms 12.4
```

---

## Step 3 — Get the project onto the GPU PC

Option A — git clone (if you push the repo somewhere):

```bash
git clone <your-repo-url> ~/aircraft
cd ~/aircraft
```

Option B — rsync from the Windows DB PC (no git remote needed):

On the DB PC, in PowerShell:

```powershell
# Make sure OpenSSH is on the GPU PC (sudo apt install openssh-server)
$gpu = "you@gpu-pc.local"
rsync -av --exclude=.venv --exclude=data/images --exclude=node_modules --exclude=__pycache__ `
    c:/Projects/fun/aircraft/ "${gpu}:~/aircraft/"
```

On the GPU PC:

```bash
cd ~/aircraft
```

You do **not** need to copy `data/images/` — the GPU pipeline doesn't read them (it generates new visuals via text-to-video). You **do** need MongoDB access — see step 4.

---

## Step 4 — Connect to the Windows DB PC's MongoDB

The GPU PC reads the `publish.shortform_script` field from the DB PC's Mongo.

On the **Windows DB PC**, edit `docker-compose.yml` and replace the Mongo `ports` line:

```yaml
ports:
  - "0.0.0.0:27017:27017"   # was "27017:27017"
```

Restart:

```powershell
docker compose down
docker compose up -d
```

Then allow inbound on port 27017 in Windows Firewall (one-time):

```powershell
New-NetFirewallRule -DisplayName "Mongo (aircraft)" -Direction Inbound -LocalPort 27017 -Protocol TCP -Action Allow
```

Find the Windows PC's LAN IP (`ipconfig` → look for IPv4 of your active adapter, e.g. `192.168.1.42`).

On the **GPU PC**:

```bash
# Test the connection (Python will pull pymongo as a dep later, this just sanity-checks)
sudo apt install -y mongodb-clients   # one-time
mongosh "mongodb://aircraft:aircraft@192.168.1.42:27017/?authSource=admin" --eval "db.aircraft.countDocuments({})"
# should print: 3929
```

Save the URI to `~/aircraft/.env`:

```bash
cat > ~/aircraft/.env << 'EOF'
MONGO_URI=mongodb://aircraft:aircraft@192.168.1.42:27017/?authSource=admin
MONGO_DB=aircraft
USER_AGENT=aircraft-db/0.1 (pilles@eev-systems.com)
EOF
```

(Replace `192.168.1.42` with your DB PC's actual IP.)

---

## Step 5 — Python environment

One venv to rule them all:

```bash
cd ~/aircraft
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools
```

Install the pipeline-side dependencies (the small list — model installs come next):

```bash
pip install -r video_pipeline/requirements.txt
```

Install PyTorch matching your CUDA (12.4):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

Sanity-check:

```bash
python -c "import torch; print('cuda:', torch.cuda.is_available(), 'device:', torch.cuda.get_device_name(0))"
# expect: cuda: True   device: NVIDIA GeForce RTX 4090
```

---

## Step 6 — Install the four models

Each model below is its own install — `pip install` and a one-time download to `~/.cache/huggingface/`.

### 6a — F5-TTS (voice)

```bash
pip install f5-tts
# Or, for the latest from source:
# git clone https://github.com/SWivid/F5-TTS && cd F5-TTS && pip install -e .

# Pre-download the default English model (~3 GB)
python -c "from f5_tts.infer.utils_infer import load_model; load_model()"
```

Record a 15-30 second clean voice sample (you, or any voice you like) — save it as `video_pipeline/voices/narrator.wav`. WAV 24 kHz mono works best.

Quick CLI test:

```bash
f5-tts_infer-cli \
  --ref_audio video_pipeline/voices/narrator.wav \
  --ref_text "This is a short reference clip in my normal speaking voice." \
  --gen_text "Testing the voice clone." \
  --output_path /tmp/test.wav

aplay /tmp/test.wav   # or play /tmp/test.wav
```

### 6b — LTX-Video (workhorse text-to-video)

```bash
pip install diffusers transformers accelerate sentencepiece imageio imageio-ffmpeg
# Diffusers supports LTX-Video natively.

# Pre-download (~14 GB)
python -c "
from diffusers import LTXPipeline
import torch
LTXPipeline.from_pretrained('Lightricks/LTX-Video', torch_dtype=torch.bfloat16)
print('ok')
"
```

### 6c — HunyuanVideo (hero shots)

HunyuanVideo is a heavier install. Two options:

**Option A — via Diffusers** (easier, slightly less control):

```bash
# Already installed above. Pre-download (~28 GB)
python -c "
from diffusers import HunyuanVideoPipeline
import torch
HunyuanVideoPipeline.from_pretrained('hunyuanvideo-community/HunyuanVideo', torch_dtype=torch.bfloat16)
print('ok')
"
```

**Option B — official repo** (better quality, more setup):

```bash
git clone https://github.com/Tencent/HunyuanVideo ~/HunyuanVideo
cd ~/HunyuanVideo
pip install -r requirements.txt
# Follow their README for model-download step
```

If you only have 24 GB VRAM, use the quantized FP8 weights (their README documents this).

### 6d — MusicGen (background music)

```bash
pip install audiocraft

# Pre-download (~3 GB for medium)
python -c "
from audiocraft.models import MusicGen
MusicGen.get_pretrained('facebook/musicgen-medium')
print('ok')
"
```

### 6e — WhisperX (subtitle alignment)

```bash
pip install whisperx

# Pre-download (~3 GB for large-v3)
python -c "
import whisperx
whisperx.load_model('large-v3', 'cuda', compute_type='float16')
print('ok')
"
```

---

## Step 7 — Configure the pipeline

```bash
cd ~/aircraft
cp video_pipeline/config.example.toml video_pipeline/config.toml
nano video_pipeline/config.toml
```

Edit these fields:

```toml
[gpu]
device = "cuda:0"

[tts]
backend = "f5-tts"
voice_sample = "video_pipeline/voices/narrator.wav"
ref_text = "This is a short reference clip in my normal speaking voice."

[video_gen]
backend = "ltx-video"
hero_backend = "hunyuan-video"
resolution = "1080x1920"
fps = 24

[mongo]
uri = "mongodb://aircraft:aircraft@192.168.1.42:27017/?authSource=admin"
db  = "aircraft"
```

---

## Step 8 — First render test

Pick a small aircraft to start with (the SR-71 has 7 shots — longer):

```bash
source .venv/bin/activate
python video_pipeline/render_short.py f-16
```

What happens:
1. Reads `publish.shortform_script` for the F-16 from Mongo
2. Generates `narration.wav` via F5-TTS (~10 sec)
3. Aligns subtitles via WhisperX (~5 sec)
4. Generates 7 video clips via LTX-Video (~3-4 min)
5. Generates background music via MusicGen (~30 sec)
6. Renders title + end cards via Pillow
7. Stitches everything via ffmpeg → `renders/military/f-16.mp4`
8. Writes `publish.shortform_render_path` back to Mongo

Open the file:

```bash
ls -lh renders/military/f-16.mp4
# transfer to your phone or watch via VLC
mpv renders/military/f-16.mp4
```

---

## Step 9 — Daily batch (4 Shorts in one go)

```bash
python video_pipeline/render_today.py
```

This picks the highest-score un-rendered aircraft per category and renders 4. Expect ~15-20 min wall time on a 4090.

---

## Step 10 — Daily cron at 03:00

```bash
crontab -e
```

Add:

```cron
0 3 * * * cd /home/$USER/aircraft && /home/$USER/aircraft/.venv/bin/python video_pipeline/render_today.py >> /home/$USER/aircraft/cron.log 2>&1
```

Done — 4 Shorts ready every morning by ~03:30.

---

## Step 11 (optional) — YouTube auto-upload

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

1. Create a Google Cloud project, enable YouTube Data API v3.
2. Make OAuth 2.0 credentials (Desktop App), download `client_secrets.json` to `~/aircraft/video_pipeline/youtube/`.
3. First run does an interactive OAuth — afterwards `token.json` is cached.

Skeleton uploader (you'd add this as `video_pipeline/upload_youtube.py`):

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def upload(file: str, title: str, description: str, tags: list[str], category_id: str = "27"):
    creds = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES).run_local_server()
    yt = build("youtube", "v3", credentials=creds)
    request = yt.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "tags": tags, "categoryId": category_id},
            "status":  {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(file, chunksize=-1, resumable=True),
    )
    response = request.execute()
    return response["id"]
```

The `title`, `description`, `tags` all come straight from the doc's `publish` subdoc.

TikTok and Reels don't have free APIs — most creators upload those manually with the per-platform caption files we already wrote to `publish_kits/<category>/<slug>/`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `torch.cuda.is_available() == False` | Re-check driver. Reboot. Then `pip install torch ... --index-url https://download.pytorch.org/whl/cu124` to ensure matching CUDA build. |
| Out of memory during HunyuanVideo | Switch to the FP8 quantized variant, or use LTX-Video as `hero_backend` too. |
| `pymongo.errors.ServerSelectionTimeoutError` | Windows firewall is blocking 27017, or `bindIp` in Mongo is still `127.0.0.1`. Re-check step 4. |
| Audio out of sync with video | The narration `adelay` filter in `steps/assemble.py` lines audio up after the title card. Increase `title_card_seconds` slightly if your TTS has a long lead-in. |
| ffmpeg can't find `subtitles` filter | You need `libass` support: `sudo apt install ffmpeg libass-dev`, then `ffmpeg -filters 2>&1 \| grep subtitles`. |
| F5-TTS produces robotic output | Your reference clip is too noisy or too short. Use a clean 20-30s WAV at 24 kHz mono. |
| MusicGen sounds vague | Make the prompt more concrete: "epic orchestral strings with low brass drones, cold and vast, 80 BPM" not just "cinematic". |
| Subtitles flash too fast | Switch `subtitles.style = "static"` in config.toml — one cue per sentence instead of per word. |

---

## Disk usage estimate

| Item | Approx size |
|---|---|
| CUDA toolkit | 6 GB |
| PyTorch + base deps | 5 GB |
| F5-TTS model | 3 GB |
| LTX-Video model | 14 GB |
| HunyuanVideo model | 28 GB (FP8 quantized: 14 GB) |
| MusicGen medium | 3 GB |
| WhisperX large-v3 | 3 GB |
| Generated renders (per Short) | ~20-40 MB |
| Workdir intermediates (kept after render) | ~200 MB per Short |
| **Total models + system** | **~65 GB minimum** |

If you want to keep ~100 days of intermediates around: + ~20 GB.

---

## What's next once the pipeline is rendering

1. **Quality pass on the first 10 Shorts.** Tune narration speed, music volume (`music_volume` in `steps/assemble.py`), subtitle styling, title-card font.
2. **Curate the voice.** Try 3-4 different reference samples; pick the one that fits the channel best.
3. **Branding overlay.** Add a fixed top-corner logo via ffmpeg `overlay` filter in `assemble.py`.
4. **Upload + analytics loop.** Once auto-upload is wired in, pipe back the video IDs to Mongo so you can correlate `composite_score` vs actual views and tune the ranking.
