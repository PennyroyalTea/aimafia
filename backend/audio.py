"""Extract audio from a video URL using yt-dlp."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable


def extract_audio(
    video_url: str,
    output_dir: Path | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> Path:
    """Download video and extract audio as mp3.

    Args:
        video_url: URL of the video (YouTube, Twitch VOD, etc.).
        output_dir: Directory to save the audio file. Uses a temp dir if None.
        progress_callback: Optional callback receiving progress strings.

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
        "--newline",  # print progress on new lines instead of \r
        video_url,
    ]

    if progress_callback is None:
        subprocess.run(cmd, check=True)
    else:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in process.stdout:  # type: ignore[union-attr]
            m = re.search(r"\[download\]\s+(\d+\.?\d*)%", line)
            if m:
                progress_callback(f"Downloading: {m.group(1)}%")
            elif "[ExtractAudio]" in line:
                progress_callback("Converting to mp3...")
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)

    audio_path = output_dir / "audio.mp3"
    if not audio_path.exists():
        # yt-dlp may produce a different filename in edge cases
        mp3_files = list(output_dir.glob("*.mp3"))
        if not mp3_files:
            raise FileNotFoundError(f"No mp3 file found in {output_dir} after extraction")
        audio_path = mp3_files[0]

    return audio_path
