"""Extract audio from a video URL using yt-dlp."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def extract_audio(video_url: str, output_dir: Path | None = None) -> Path:
    """Download video and extract audio as mp3.

    Args:
        video_url: URL of the video (YouTube, Twitch VOD, etc.).
        output_dir: Directory to save the audio file. Uses a temp dir if None.

    Returns:
        Path to the extracted mp3 file.
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="mafia_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "audio.%(ext)s")

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "3",  # reasonable quality, smaller file
        "--output", output_template,
        "--no-playlist",
        video_url,
    ]

    subprocess.run(cmd, check=True)

    audio_path = output_dir / "audio.mp3"
    if not audio_path.exists():
        # yt-dlp may produce a different filename in edge cases
        mp3_files = list(output_dir.glob("*.mp3"))
        if not mp3_files:
            raise FileNotFoundError(f"No mp3 file found in {output_dir} after extraction")
        audio_path = mp3_files[0]

    return audio_path
