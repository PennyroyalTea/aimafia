"""Pydantic models shared across the mafia analyzer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


# --- Transcript models ---


class Utterance(BaseModel):
    speaker: str
    text: str
    start: float
    end: float


class Transcript(BaseModel):
    utterances: list[Utterance] = []
    full_text: str = ""

    def as_dialogue(self) -> str:
        """Return a human-readable dialogue string."""
        lines: list[str] = []
        for u in self.utterances:
            ts = f"[{_fmt_time(u.start)}-{_fmt_time(u.end)}]"
            lines.append(f"{ts} {u.speaker}: {u.text}")
        return "\n".join(lines)


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# --- Diarization improver models ---


class SpeakerMapping(BaseModel):
    original_id: str
    resolved_name: str


class ImprovedTranscript(BaseModel):
    mappings: list[SpeakerMapping]
    utterances: list[Utterance]


# --- Summarizer models ---


class PlayerSummary(BaseModel):
    player_name: str
    role: str | None = None
    summary: str


class GameSummary(BaseModel):
    title: str = ""
    winner: str
    summary: str
    key_moments: list[str] = []
    players: list[PlayerSummary] = []


class PersonalAdvice(BaseModel):
    player_name: str
    role: str | None = None
    mistakes: list[str] = []
    good_plays: list[str] = []
    advice: str


class GameAnalysis(BaseModel):
    summary: GameSummary
    advice: list[PersonalAdvice] = []


# --- Pipeline / API models ---


class PipelineStep(str, Enum):
    downloading = "downloading"
    transcribing = "transcribing"
    improving_diarization = "improving_diarization"
    generating_analysis = "generating_analysis"
    done = "done"
    failed = "failed"


class GameStatus(BaseModel):
    game_id: str
    step: PipelineStep
    detail: str = ""


class InterestSubmission(BaseModel):
    name: str
    email: str
    role: str  # "organiser" | "player" | "both"
    location: str
    comment: str = ""


class GameResult(BaseModel):
    game_id: str
    analysis: GameAnalysis | None = None
    error: str | None = None
