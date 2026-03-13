# Mafia Game Analyzer

Web app that analyzes mafia game videos: extracts audio, transcribes with speaker diarization, splits into individual games, and generates per-player coaching reports.

## Requirements

- Python 3.11+
- Node.js 18+
- `yt-dlp` and `ffmpeg` on your system
- ElevenLabs API key (transcription)
- Anthropic API key (analysis)

```bash
# macOS
brew install yt-dlp ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
pip install yt-dlp
```

## Setup

```bash
# Backend
pip install .
cp .env.example .env  # add your API keys

# Frontend
cd frontend && npm install
```

## Running

```bash
# Start backend (port 8000)
uvicorn mafia_analyzer.api.app:app --reload --port 8000

# Start frontend (port 5173, proxies /api to backend)
cd frontend && npm run dev
```

Open http://localhost:5173

## How it works

1. **Input** -- paste a YouTube/video URL or upload an audio/video file directly
2. **Audio extraction** -- downloads video via `yt-dlp` and extracts audio (skipped for direct uploads)
3. **Transcription** -- sends audio to ElevenLabs Scribe v2 with speaker diarization
4. **Game splitting** -- Claude identifies individual game boundaries within the session
5. **Diarization improvement** -- Claude maps generic speaker IDs to player identities
6. **Analysis** -- Claude generates per-game summaries and personalized coaching advice

Progress is streamed to the browser in real time via SSE.
