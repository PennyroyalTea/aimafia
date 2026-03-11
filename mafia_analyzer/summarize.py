"""Summarize a mafia game transcript into per-player reports using Claude."""

from __future__ import annotations

import os

import anthropic

from mafia_analyzer.transcribe import Transcript

SYSTEM_PROMPT = """\
You are an expert analyst of the social deduction game "Mafia" (also known as "Werewolf").
You will receive a transcript of a mafia game with speaker-diarized dialogue.

The video may contain pre-game or post-game commentary by the judge/host (e.g. \
introductions, rule explanations, post-game discussion, role reveals). Separate this \
from the actual gameplay. Use any post-game role reveals as ground truth for your analysis.

Your job is to produce a structured summary of the game, including:
1. A brief overall game summary (who won, key turning points).
2. A personalised report for EACH player (not the judge/host), covering:
   - Their role (use post-game reveals when available; if not revealed, say it is unknown).
   - Key moves and speeches they made.
   - Voting behaviour and accusations.
   - Notable strategic moments (bluffs, defences, reveals).

IMPORTANT: Do NOT guess information that is unclear from the transcript. If you are \
unsure about something (e.g. a player's role, who was eliminated in a particular round, \
or any other game detail), ask the user for clarification instead of guessing. Format \
your questions as a numbered list prefixed with "QUESTIONS:" on the first line. Do not \
include any analysis when asking questions — only ask the questions.

When you have enough information, produce the full analysis. Format the output in \
Markdown. Use the speaker IDs from the transcript. Write the analysis in the same \
language as the transcript.
"""


def _has_questions(text: str) -> bool:
    """Check whether the model response is a clarification request."""
    return text.strip().startswith("QUESTIONS:")


def summarize(
    transcript: Transcript,
    *,
    ask_fn: callable | None = None,
    max_rounds: int = 5,
) -> str:
    """Generate per-player game summary from transcript.

    The model may ask clarifying questions (e.g. about roles) instead of
    guessing.  When *ask_fn* is provided it will be called with the
    question text and should return the user's answer.  If *ask_fn* is
    ``None``, questions are not supported and the model is asked to do its
    best with the available information.

    Args:
        transcript: Diarized transcript of the mafia game.
        ask_fn: Optional callback ``(questions: str) -> str`` for user Q&A.
        max_rounds: Maximum number of Q&A rounds before forcing output.

    Returns:
        Markdown-formatted game analysis.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    dialogue = transcript.as_dialogue()

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                "Here is the transcript of a mafia game:\n\n"
                f"{dialogue}\n\n"
                "Please provide a full game analysis with personalised player reports."
            ),
        }
    ]

    for _ in range(max_rounds):
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        response_text = message.content[0].text

        if not _has_questions(response_text):
            return response_text

        # Model wants clarification
        if ask_fn is None:
            # No way to ask the user — tell the model to proceed anyway
            messages.append({"role": "assistant", "content": response_text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "I don't have that information. "
                        "Please proceed with the analysis using what is available "
                        "and mark uncertain details as unknown."
                    ),
                }
            )
            continue

        answer = ask_fn(response_text)
        messages.append({"role": "assistant", "content": response_text})
        messages.append({"role": "user", "content": answer})

    # Exhausted rounds — force final output
    messages.append(
        {
            "role": "user",
            "content": "Please produce the final analysis now with whatever information you have.",
        }
    )
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return message.content[0].text
