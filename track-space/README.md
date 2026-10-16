---
title: Unmix Track Lab
emoji: 🎧
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Unmix Track Lab inference service

This is a separate inference service for the GitHub Pages frontend. It uses the same
Audio Separator ONNX MDX preset as the main project, but runs outside Render's 512 MiB
limit. The frontend and Mix Lab remain hosted in the existing project.

## Deploy (free CPU Space)

1. Create a **public Docker Space** on Hugging Face named `unmix-track-lab`.
2. Upload the contents of this folder to the Space's repository root (not the folder itself).
3. Wait for the Space to build. First inference downloads the model and can take several minutes.
4. The API base URL will be `https://YOUR-USERNAME-unmix-track-lab.hf.space`.
5. Set the GitHub repository Actions variable `UNMIX_TRACK_API_BASE` to that exact URL, then rerun the Pages workflow.

Free CPU Spaces can sleep or be slow on first request. This service is intended for a submission demo, not guaranteed always-on production.

## API

- `GET /api/health`
- `POST /api/track-lab/separate` with multipart field `track`
- Stem audio files are served from `/media/{job}/{filename}`

Allowed uploads: WAV, FLAC, MP3, M4A, OGG; maximum 100 MB and 20 minutes.
