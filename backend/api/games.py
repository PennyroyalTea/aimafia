"""Game store backed by MongoDB and pipeline runner."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend import mongo
from backend.llm.diarization_improver import improve_diarization
from backend.llm.summarizer import generate_game_analysis
from backend.models import (
    GameAnalysis,
    GameResult,
    GameStatus,
    ImprovedTranscript,
    PipelineStep,
    Transcript,
)
from backend.transcribe import transcribe

logger = logging.getLogger(__name__)


class GameStore:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self.running_tasks: dict[str, asyncio.Task] = {}

    async def create_game(
        self,
        language: str,
        source_filename: str | None = None,
        game_context: str = "",
    ) -> str:
        game_id = str(uuid4())
        doc = {
            "_id": game_id,
            "source_filename": source_filename,
            "language": language,
            "game_context": game_context,
            "created_at": datetime.now(timezone.utc),
            "upload_status": {"step": PipelineStep.downloading.value, "detail": ""},
            "transcript": None,
            "diarization": None,
            "analysis": None,
            "error": None,
        }
        await mongo.db.games.insert_one(doc)
        self._subscribers[game_id] = []
        return game_id

    async def subscribe(self, game_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(game_id, []).append(queue)
        # Send current status immediately
        game = await self.get_game(game_id)
        if game:
            status = GameStatus(
                game_id=game_id,
                step=PipelineStep(game["upload_status"]["step"]),
                detail=game["upload_status"].get("detail", ""),
            )
            queue.put_nowait(status)
            # If already finished, also send the result
            step = PipelineStep(game["upload_status"]["step"])
            if step in (PipelineStep.done, PipelineStep.failed):
                analysis = (
                    GameAnalysis.model_validate(game["analysis"])
                    if game.get("analysis")
                    else None
                )
                result = GameResult(
                    game_id=game_id,
                    analysis=analysis,
                    error=game.get("error"),
                )
                queue.put_nowait(result)
        return queue

    def unsubscribe(self, game_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(game_id, [])
        if queue in subs:
            subs.remove(queue)

    async def _notify(self, game_id: str, event: GameStatus | GameResult) -> None:
        for queue in self._subscribers.get(game_id, []):
            await queue.put(event)

    async def update_status(
        self, game_id: str, step: PipelineStep, detail: str = ""
    ) -> None:
        status = GameStatus(game_id=game_id, step=step, detail=detail)
        await mongo.db.games.update_one(
            {"_id": game_id},
            {"$set": {"upload_status": {"step": step.value, "detail": detail}}},
        )
        await self._notify(game_id, status)

    async def set_result(self, game_id: str, result: GameResult) -> None:
        step = PipelineStep.done if result.error is None else PipelineStep.failed
        status = GameStatus(
            game_id=game_id,
            step=step,
            detail=result.error or "",
        )
        update: dict = {
            "upload_status": {"step": step.value, "detail": result.error or ""},
            "error": result.error,
        }
        if result.analysis is not None:
            update["analysis"] = result.analysis.model_dump()
        await mongo.db.games.update_one({"_id": game_id}, {"$set": update})
        await self._notify(game_id, status)
        await self._notify(game_id, result)

    async def get_game(self, game_id: str) -> dict | None:
        return await mongo.db.games.find_one({"_id": game_id})

    async def find_cached_transcript_by_hash(
        self, audio_hash: str, language: str, exclude_game_id: str,
    ) -> Transcript | None:
        """Find a saved transcript from a previous game with the same audio hash and language."""
        doc = await mongo.db.games.find_one(
            {
                "_id": {"$ne": exclude_game_id},
                "audio_hash": audio_hash,
                "language": language,
                "transcript": {"$ne": None},
                "error": None,
            },
            projection={"transcript": 1},
        )
        if doc and doc.get("transcript"):
            return Transcript.model_validate(doc["transcript"])
        return None


game_store = GameStore()


async def run_pipeline(
    game_id: str,
    language: str,
    source_file: Path,
    game_context: str = "",
) -> None:
    """Run the full analysis pipeline for a game."""
    loop = asyncio.get_running_loop()

    try:
        audio_path = source_file
        await game_store.update_status(
            game_id, PipelineStep.downloading,
            f"Using uploaded file: {source_file.name}",
        )

        # Compute content hash for transcript caching
        audio_hash = await asyncio.to_thread(
            lambda: hashlib.sha256(audio_path.read_bytes()).hexdigest()
        )
        await mongo.db.games.update_one(
            {"_id": game_id}, {"$set": {"audio_hash": audio_hash}},
        )

        # Check for cached transcript by content hash
        cached = await game_store.find_cached_transcript_by_hash(
            audio_hash, language, game_id,
        )
        if cached is not None:
            transcript = cached
            await mongo.db.games.update_one(
                {"_id": game_id},
                {"$set": {"transcript": transcript.model_dump()}},
            )
            await game_store.update_status(
                game_id, PipelineStep.transcribing,
                f"Reusing cached transcript ({len(transcript.utterances)} utterances)",
            )
        else:
            # Step 2: Transcribe
            await game_store.update_status(
                game_id, PipelineStep.transcribing,
                "Sending audio to ElevenLabs (no progress available)...",
            )
            transcript = await asyncio.to_thread(transcribe, audio_path, language)
            await mongo.db.games.update_one(
                {"_id": game_id},
                {"$set": {"transcript": transcript.model_dump()}},
            )
            await game_store.update_status(
                game_id, PipelineStep.transcribing,
                f"Done -- {len(transcript.utterances)} utterances",
            )

        # Step 3: Improve diarization on full transcript
        await game_store.update_status(
            game_id, PipelineStep.improving_diarization,
            "Identifying players...",
        )
        improved = await asyncio.to_thread(
            improve_diarization, transcript.utterances
        )
        n_players = len(
            [m for m in improved.mappings if m.resolved_name != "Judge"]
        )
        await mongo.db.games.update_one(
            {"_id": game_id},
            {"$set": {"diarization": improved.model_dump()}},
        )
        await game_store.update_status(
            game_id, PipelineStep.improving_diarization,
            f"Found {n_players} players",
        )

        # Step 4: Generate analysis
        await game_store.update_status(
            game_id, PipelineStep.generating_analysis,
            "Generating game analysis...",
        )
        analysis = await asyncio.to_thread(
            generate_game_analysis, improved, 1, language, game_context
        )
        await mongo.db.games.update_one(
            {"_id": game_id},
            {"$set": {"analysis": analysis.model_dump()}},
        )
        await game_store.update_status(
            game_id, PipelineStep.generating_analysis,
            "Done",
        )

        result = GameResult(game_id=game_id, analysis=analysis)
        await game_store.set_result(game_id, result)

    except Exception:
        import traceback

        logger.exception("Pipeline failed for game %s", game_id)
        error_result = GameResult(
            game_id=game_id, error=traceback.format_exc()
        )
        await game_store.set_result(game_id, error_result)

    finally:
        # Cleanup temp audio files
        try:
            shutil.rmtree(source_file.parent, ignore_errors=True)
        except Exception:
            pass
        game_store.running_tasks.pop(game_id, None)


async def run_reanalysis(
    game_id: str,
    language: str,
    game_context: str = "",
) -> None:
    """Re-run only the analysis step using existing transcript + diarization."""
    try:
        doc = await game_store.get_game(game_id)
        if not doc:
            raise ValueError(f"Game {game_id} not found")

        improved = ImprovedTranscript.model_validate(doc["diarization"])

        await game_store.update_status(
            game_id, PipelineStep.generating_analysis,
            "Re-generating analysis with new context...",
        )
        analysis = await asyncio.to_thread(
            generate_game_analysis, improved, 1, language, game_context
        )
        await mongo.db.games.update_one(
            {"_id": game_id},
            {"$set": {"analysis": analysis.model_dump()}},
        )
        await game_store.update_status(
            game_id, PipelineStep.generating_analysis, "Done",
        )

        result = GameResult(game_id=game_id, analysis=analysis)
        await game_store.set_result(game_id, result)

    except Exception:
        import traceback

        logger.exception("Re-analysis failed for game %s", game_id)
        error_result = GameResult(
            game_id=game_id, error=traceback.format_exc()
        )
        await game_store.set_result(game_id, error_result)

    finally:
        game_store.running_tasks.pop(game_id, None)
