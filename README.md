# Mafia Game Analyzer

Analyze mafia game videos: extract audio, transcribe with speaker diarization, and get per-player game reports.

## Setup

```bash
pip install .
```

Requires `yt-dlp` and `ffmpeg` on your system:
```bash
# macOS
brew install yt-dlp ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
pip install yt-dlp
```

Set your API keys:
```bash
export ELEVENLABS_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key
```

## Usage

```bash
# Basic usage — prints report to stdout
mafia-analyze "https://youtube.com/watch?v=..."

# Save report and transcript
mafia-analyze "https://youtube.com/watch?v=..." -o report.md --transcript-out transcript.txt

# Specify language (default: ru)
mafia-analyze "https://youtube.com/watch?v=..." -l en
```

## How it works

1. **Audio extraction** — downloads video via `yt-dlp` and extracts audio as mp3
2. **Transcription** — sends audio to ElevenLabs Scribe v2 with speaker diarization
3. **Analysis** — feeds the diarized transcript to Claude for per-player game summary
