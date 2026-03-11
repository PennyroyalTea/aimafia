"""Generate game summaries and personal coaching advice."""

from __future__ import annotations

import json
import os

import anthropic

from mafia_analyzer.llm import extract_json
from mafia_analyzer.llm.prompts import (
    GAME_SUMMARY_SYSTEM,
    PERSONAL_ADVICE_SYSTEM,
    language_instruction,
)
from mafia_analyzer.models import (
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
    summary_msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=GAME_SUMMARY_SYSTEM + lang_suffix,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Game number: {game_number}\n\n"
                    f"Transcript:\n\n{transcript_text}"
                ),
            }
        ],
    )

    summary_data = extract_json(summary_msg.content[0].text)
    summary = GameSummary.model_validate(summary_data)

    # Pass 2: Personal advice
    advice_msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=PERSONAL_ADVICE_SYSTEM + lang_suffix,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Game transcript:\n\n{transcript_text}\n\n"
                    f"Game summary:\n{json.dumps(summary_data, ensure_ascii=False)}"
                ),
            }
        ],
    )

    advice_data = extract_json(advice_msg.content[0].text)
    advice_list = [
        PersonalAdvice.model_validate(a) for a in advice_data["advice"]
    ]

    return GameAnalysis(summary=summary, advice=advice_list)
