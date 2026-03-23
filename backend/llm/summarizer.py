"""Generate game summaries and personal coaching advice."""

from __future__ import annotations

import json
import os

import anthropic

from backend.llm import extract_json
from backend.llm.prompts import (
    GAME_SUMMARY_SYSTEM,
    PERSONAL_ADVICE_SYSTEM,
    language_instruction,
)
from backend.models import (
    GameAnalysis,
    GameSummary,
    ImprovedTranscript,
    PersonalAdvice,
)


def _format_transcript(transcript: ImprovedTranscript) -> str:
    lines: list[str] = []
    for u in transcript.utterances:
        lines.append(f"{u.speaker}: {u.text}")
    return "\n".join(lines)


def _create_message(
    client: anthropic.Anthropic,
    system: str,
    user_content: str,
    max_tokens: int = 16384,
) -> str:
    """Call the API and raise on truncation."""
    msg = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    if msg.stop_reason == "max_tokens":
        raise ValueError(
            f"LLM response truncated at {max_tokens} tokens. "
            "The output was too long to fit within the limit."
        )
    return msg.content[0].text


def generate_game_analysis(
    transcript: ImprovedTranscript,
    game_number: int,
    language: str = "ru",
) -> GameAnalysis:
    """Generate full game analysis: summary + personal advice.

    Args:
        transcript: Improved transcript with resolved speaker names.
        game_number: Which game number this is in the session.
        language: Language code (ru/en/uk) for the output text.

    Returns:
        GameAnalysis with summary and per-player advice.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    transcript_text = _format_transcript(transcript)
    lang_suffix = "\n\n" + language_instruction(language)

    # Pass 1: Game summary
    summary_text = _create_message(
        client,
        system=GAME_SUMMARY_SYSTEM + lang_suffix,
        user_content=(
            f"Game number: {game_number}\n\n"
            f"Transcript:\n\n{transcript_text}"
        ),
    )
    summary_data = extract_json(summary_text)
    summary = GameSummary.model_validate(summary_data)

    # Pass 2: Personal advice
    advice_text = _create_message(
        client,
        system=PERSONAL_ADVICE_SYSTEM + lang_suffix,
        user_content=(
            f"Game transcript:\n\n{transcript_text}\n\n"
            f"Game summary:\n{json.dumps(summary_data, ensure_ascii=False)}"
        ),
    )
    advice_data = extract_json(advice_text)
    advice_list = [
        PersonalAdvice.model_validate(a) for a in advice_data["advice"]
    ]

    return GameAnalysis(summary=summary, advice=advice_list)
