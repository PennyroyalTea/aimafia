"""Split a transcript into individual games."""

from __future__ import annotations

import os

import anthropic

from backend.llm import extract_json
from backend.llm.prompts import GAME_SPLITTER_SYSTEM
from backend.models import SplitResult, Transcript


def split_games(transcript: Transcript) -> SplitResult:
    """Identify game boundaries within a full session transcript.

    Args:
        transcript: Full diarized transcript of the session.

    Returns:
        SplitResult with utterance index ranges for each game.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Build numbered utterance list for the LLM
    lines: list[str] = []
    for i, u in enumerate(transcript.utterances):
        lines.append(f"[{i}] {u.speaker}: {u.text}")
    utterance_text = "\n".join(lines)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=GAME_SPLITTER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is the transcript with {len(transcript.utterances)} utterances:\n\n"
                    f"{utterance_text}"
                ),
            }
        ],
    )

    raw = message.content[0].text
    data = extract_json(raw)
    return SplitResult.model_validate(data)
