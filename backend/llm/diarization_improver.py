"""Improve speaker diarization by mapping generic IDs to player identities."""

from __future__ import annotations

import os

import anthropic

from backend.llm import extract_json
from backend.llm.prompts import DIARIZATION_IMPROVER_SYSTEM
from backend.models import ImprovedTranscript, Utterance


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

    chunks: list[str] = []
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=DIARIZATION_IMPROVER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Here is the game transcript:\n\n{transcript_text}",
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)

    raw = "".join(chunks)
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

    from backend.models import SpeakerMapping

    return ImprovedTranscript(
        mappings=[SpeakerMapping.model_validate(m) for m in data["mappings"]],
        utterances=improved_utterances,
    )
