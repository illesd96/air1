# GPU PC bootstrap — one-script install

For setting up the Linux GPU machine that renders the Shorts. Designed so you run **one** command on the GPU PC and it does everything end-to-end. The bootstrap auto-detects your distro and GPU vendor and runs the right stage scripts.

## Supported platforms

| Distro | GPU | Path | Tested on |
|---|---|---|---|
| **Ubuntu 22.04 / 24.04** | NVIDIA (RTX 30/40-series, 24 GB+) | `ubuntu_nvidia/` | RTX 4090 |
| **Fedora 41 / 42 / 43** | AMD RDNA 3 / 3.5 (incl. Strix Halo iGPU) | `fedora_amd/` | Framework Desktop, Ryzen AI Max+ 395 / Radeon 8060S |

If you're on a combo the script doesn't recognize, it'll tell you and you can set `PLATFORM=<name>` to force one.

## Prerequisites

- GPU PC on the same LAN as the Windows DB PC
- The Windows DB PC's MongoDB exposed on the LAN (one-time setup below)
- ~500 GB free disk on the GPU PC (models alone are ~65 GB)

## Step 1 — On the Windows DB PC (once)

### a) Expose MongoDB to the LAN

Edit `c:\Projects\fun\aircraft\docker-compose.yml` and change the mongo `ports` block to bind on all interfaces:

```yaml
ports:
  - "0.0.0.0:27017:27017"
```

Restart:

```powershell
docker compose down
docker compose up -d
```

### b) Allow inbound port 27017 (Windows Firewall)

```powershell
New-NetFirewallRule -DisplayName "Mongo (aircraft)" -Direction Inbound -LocalPort 27017 -Protocol TCP -Action Allow
```

Note the LAN IP of the Windows machine (`ipconfig` → IPv4 of your active adapter).

### c) Copy the project to the GPU PC

The Linux PC needs `sudo dnf install -y openssh-server && sudo systemctl enable --now sshd` (Fedora) or `sudo apt install -y openssh-server` (Ubuntu) first.

From PowerShell on Windows:

```powershell
.\gpu_install\rsync_from_db_pc.ps1 -GpuUser <linux-user> -GpuHost <gpu-host-or-ip>
```

If you don't have rsync on Windows, install Git for Windows (it bundles rsync) or just `scp -r` the folder.

## Step 2 — On the Linux GPU PC

```bash
cd ~/aircraft
bash gpu_install/bootstrap.sh
```

That's it. The bootstrap detects your platform, then runs five stages with checkpointing:

| Stage | What | Re-login / Reboot? |
|---|---|---|
| `00_system` | distro packages, ffmpeg, GPU driver/runtime (CUDA or ROCm) | **Possibly**, see below |
| `01_python_env` | Python 3.11 venv, PyTorch matched to GPU | no |
| `02_models` | F5-TTS + diffusion video models + MusicGen + WhisperX | no (~50 GB download) |
| `03_configure` | Mongo URI + voice sample + ref text | interactive prompts |
| `04_verify` | imports, Mongo, ffmpeg check + optional test render | interactive |

### When you'll be told to reboot / re-login

- **Ubuntu + NVIDIA:** after first run if a fresh driver was installed.
- **Fedora + AMD:** after first run if you weren't already in the `render` group (needed to talk to the GPU). Log out and back in (or reboot), then re-run `bash gpu_install/bootstrap.sh` — it picks up where it stopped.

## Stage-3 prompts

1. **DB PC's LAN IP** — e.g. `192.168.1.42`
2. **Voice sample path** — a 15-30s WAV/MP3 in your speaking voice. Leave blank to use the F5-TTS default voice (you can swap later).
3. **Reference text** — what you actually said in that sample. Press Enter for a generic default.

## After bootstrap

```bash
source .venv/bin/activate

# Render one Short
python video_pipeline/render_short.py f-16

# Render today's batch (4 — one per category)
python video_pipeline/render_today.py
```

## Daily cron

```bash
crontab -e
```

Add:

```cron
0 3 * * * cd /home/$USER/aircraft && /home/$USER/aircraft/.venv/bin/python video_pipeline/render_today.py >> /home/$USER/aircraft/cron.log 2>&1
```

## Resuming / re-running stages

State is tracked in `gpu_install/.state/`:

```bash
ls gpu_install/.state/
# 00_system.done  01_python_env.done  02_models.done  03_configure.done  04_verify.done

rm gpu_install/.state/02_models.done
bash gpu_install/bootstrap.sh
```

---

## Platform-specific notes

### Fedora + AMD (Framework Desktop / Strix Halo)

The Framework Desktop with Ryzen AI Max+ 395 (Radeon 8060S iGPU, gfx1151) is a great fit for this pipeline, with three things to know:

1. **Unified memory wins for big models.** 128 GB shared between CPU and GPU means LTX-Video and MusicGen run with room to spare. PyTorch on ROCm exposes the iGPU as if it were `cuda:0`.

2. **HunyuanVideo is skipped.** The model is too compute-heavy for an iGPU. Hero shots fall back to LTX-Video, which is still very capable. If you ever want HunyuanVideo, do it on a separate NVIDIA box.

3. **gfx1151 needs an env override.** `HSA_OVERRIDE_GFX_VERSION=11.0.0` and `PYTORCH_ROCM_ARCH=gfx1100` tell PyTorch to use the gfx1100 (RDNA 3) kernel set, which works on RDNA 3.5. The bootstrap adds these to `~/.bashrc` automatically.

**Expected per-Short render time:** ~10-15 minutes on Strix Halo (vs ~4 min on an RTX 4090). 4 Shorts/day is well within reach — that's ~1 hour of GPU time per day.

### Ubuntu + NVIDIA (RTX 30/40 series)

The classic path. Uses CUDA 12.4 + the standard NVIDIA driver. Both LTX-Video (workhorse) and HunyuanVideo (hero shots) are enabled.

**Expected per-Short render time:** ~3-5 minutes on RTX 4090. The bottleneck is HunyuanVideo for the hero shot; LTX-Video is real-time-ish.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `torch.cuda.is_available() == False` (NVIDIA) | Re-check driver. Reboot. Then `pip install torch ... --index-url https://download.pytorch.org/whl/cu124`. |
| `torch.cuda.is_available() == False` (AMD) | Make sure you're in the `render` and `video` groups (`id -nG`). Log out + back in. Confirm `rocminfo` lists your GPU. |
| `HIP error: invalid device function` on AMD | `export HSA_OVERRIDE_GFX_VERSION=11.0.0` and re-run. Already in `~/.bashrc` but a fresh shell may not have sourced it. |
| Out of memory during HunyuanVideo (NVIDIA) | Switch to FP8 quantized weights, or set `hero_backend = "ltx-video"` in `config.toml`. |
| `pymongo.errors.ServerSelectionTimeoutError` | Windows firewall blocking 27017, or Mongo still bound to 127.0.0.1. Re-check the DB-PC setup. |
| Subtitles flash too fast | Switch `subtitles.style = "static"` in `config.toml`. |
| F5-TTS produces robotic output | Reference clip too noisy or too short. Use a clean 20-30s mono WAV at 24 kHz. |
| MusicGen sounds vague | Make the music prompt more concrete: "epic orchestral strings with low brass drones, 80 BPM" not just "cinematic". |
