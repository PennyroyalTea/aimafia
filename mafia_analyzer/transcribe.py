"""Transcribe audio with speaker diarization via ElevenLabs Scribe."""

from __future__ import annotations

import os
from pathlib import Path

from elevenlabs import ElevenLabs

from mafia_analyzer.models import Transcript, Utterance

# Re-export for backward compatibility
__all__ = ["Utterance", "Transcript", "transcribe"]


def transcribe(audio_path: Path, language_code: str = "ru") -> Transcript:
    """Transcribe audio file with speaker diarization.

    Args:
        audio_path: Path to the audio file.
        language_code: BCP-47 language code (default "ru" for Russian).

    Returns:
        Transcript with per-speaker utterances.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set")

    client = ElevenLabs(
        api_key=api_key,
        timeout=1800.0,
    )

    with open(audio_path, "rb") as f:
        result = client.speech_to_text.convert(
            file=f,
            model_id="scribe_v2",
            diarize=True,
            language_code=language_code,
            request_options={"timeout_in_seconds": 1800},
        )

    # Group consecutive words by speaker into utterances
    utterances: list[Utterance] = []
    current_speaker: str | None = None
    current_words: list[str] = []
    current_start: float = 0.0
    current_end: float = 0.0

    for word in result.words:
        if word.type != "word":
            continue
        speaker = word.speaker_id or "unknown"
        if speaker != current_speaker:
            if current_words:
                utterances.append(Utterance(
                    speaker=current_speaker or "unknown",
                    text=" ".join(current_words),
                    start=current_start,
                    end=current_end,
                ))
            current_speaker = speaker
            current_words = [word.text]
            current_start = word.start
            current_end = word.end
        else:
            current_words.append(word.text)
            current_end = word.end

    if current_words:
        utterances.append(Utterance(
            speaker=current_speaker or "unknown",
            text=" ".join(current_words),
            start=current_start,
            end=current_end,
        ))

    return Transcript(
        utterances=utterances,
        full_text=result.text,
    )
