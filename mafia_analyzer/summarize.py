"""Summarize a mafia game transcript into per-player reports using Claude."""

from __future__ import annotations

import os

import anthropic

from mafia_analyzer.transcribe import Transcript

SYSTEM_PROMPT = """\
You are an expert analyst of the social deduction game "Mafia" (also known as "Werewolf").
You will receive a transcript of a mafia game with speaker-diarized dialogue.

Your job is to produce a structured summary of the game, including:
1. A brief overall game summary (who won, key turning points).
2. A personalised report for EACH speaker/player, covering:
   - Their likely role (if deducible from context).
   - Key moves and speeches they made.
   - Voting behaviour and accusations.
   - Notable strategic moments (bluffs, defences, reveals).

Format the output in Markdown. Use the speaker IDs from the transcript.
Write the analysis in the same language as the transcript.
"""


def summarize(transcript: Transcript) -> str:
    """Generate per-player game summary from transcript.

    Args:
        transcript: Diarized transcript of the mafia game.

    Returns:
        Markdown-formatted game analysis.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    dialogue = transcript.as_dialogue()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Here is the transcript of a mafia game:\n\n"
                    f"{dialogue}\n\n"
                    "Please provide a full game analysis with personalised player reports."
                ),
            }
        ],
    )

    return message.content[0].text
