"""Improve speaker diarization by mapping generic IDs to player identities."""

from __future__ import annotations

import os

import anthropic

from mafia_analyzer.llm import extract_json
from mafia_analyzer.llm.prompts import DIARIZATION_IMPROVER_SYSTEM
from mafia_analyzer.models import ImprovedTranscript, Utterance


def improve_diarization(utterances: list[Utterance]) -> ImprovedTranscript:
    """Map generic speaker IDs to player identities using context clues.

    Args:
        utterances: Utterances from a single game with generic speaker IDs.

    Returns:
        ImprovedTranscript with resolved speaker names.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Format transcript for the LLM
    lines: list[str] = []
    for u in utterances:
        lines.append(f"{u.speaker}: {u.text}")
    transcript_text = "\n".join(lines)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=DIARIZATION_IMPROVER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Here is the game transcript:\n\n{transcript_text}",
            }
        ],
    )

    raw = message.content[0].text
    data = extract_json(raw)

    # Build mapping dict
    mapping = {m["original_id"]: m["resolved_name"] for m in data["mappings"]}

    # Apply mappings to utterances
    improved_utterances = [
        Utterance(
            speaker=mapping.get(u.speaker, u.speaker),
            text=u.text,
            start=u.start,
            end=u.end,
        )
        for u in utterances
    ]

    from mafia_analyzer.models import SpeakerMapping

    return ImprovedTranscript(
        mappings=[SpeakerMapping.model_validate(m) for m in data["mappings"]],
        utterances=improved_utterances,
    )
