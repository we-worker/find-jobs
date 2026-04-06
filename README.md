# Screen AI Capture Tool

## Overview

This project listens for a global hotkey on Windows, grabs a short burst of frames
from an Android IP Camera MJPEG stream, chooses the most stable frame, rectifies the
computer screen, sends the corrected image to a vision model, and serves the latest
result on a LAN web page.

## Features

- Global hotkey trigger that is not tied to the focused window
- MJPEG burst capture from Android IP Camera
- Best-frame selection using sharpness, quad confidence, and stability
- Perspective correction for photographed computer screens
- OpenAI-compatible vision model integration
- FastAPI LAN page with latest result and recent history
- File-based storage only, no database

## Setup

1. Install Python 3.11 or newer.
2. Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Edit `config.yaml`:

- Set `stream_url` to your Android IP Camera stream URL
- Set `stream_verify_ssl` based on the camera certificate
- Set `stream_username` and `stream_password` if the camera app requires login
- Set `ai.base_url`, `ai.api_key`, and `ai.model`
- Set `ai.verify_ssl` based on your model endpoint certificate setup

4. Start the app:

```powershell
python app.py
```

## Usage

- Press the configured hotkey, default `space`
- Wait about 1 to 2 seconds
- Open `http://<your-pc-ip>:8000` from devices on the same LAN

## Notes

- On Windows, the `keyboard` package may require elevated privileges to register global hotkeys reliably.
- If your Android IP Camera stream uses a self-signed certificate, set `stream_verify_ssl: false`.
- Output files are written under `data/`.

## Troubleshooting

- Cannot capture frames: verify the phone IP, port, and camera app stream URL
- Screen detection fails: reduce glare and make the screen border more visible
- AI analysis fails: check API key, base URL, model name, and network reachability
