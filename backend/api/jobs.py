"""Job store backed by MongoDB and pipeline runner."""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.audio import extract_audio
from backend import mongo
from backend.llm.diarization_improver import improve_diarization
from backend.llm.game_splitter import split_games
from backend.llm.summarizer import generate_game_analysis
from backend.models import (
    GameAnalysis,
    JobResult,
    JobStatus,
    PipelineStep,
    Transcript,
)
from backend.transcribe import transcribe

logger = logging.getLogger(__name__)


class JobStore:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self.running_tasks: dict[str, asyncio.Task] = {}

    async def create_job(self, video_url: str, language: str) -> str:
        job_id = str(uuid4())
        doc = {
            "_id": job_id,
            "video_url": video_url,
            "language": language,
            "created_at": datetime.now(timezone.utc),
            "status": {"step": PipelineStep.downloading.value, "detail": ""},
            "transcript": None,
            "split": None,
            "diarizations": [],
            "analyses": [],
            "result": None,
        }
        await mongo.db.jobs.insert_one(doc)
        self._subscribers[job_id] = []
        return job_id

    async def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(job_id, []).append(queue)
        # Send current status immediately
        job = await self.get_job(job_id)
        if job:
            status = JobStatus(
                job_id=job_id,
                step=PipelineStep(job["status"]["step"]),
                detail=job["status"].get("detail", ""),
            )
            queue.put_nowait(status)
            # If already finished, also send the result
            if job.get("result") is not None:
                result = JobResult(
                    job_id=job_id,
                    games=[GameAnalysis.model_validate(g) for g in job["result"].get("games", [])],
                    error=job["result"].get("error"),
                )
                queue.put_nowait(result)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(job_id, [])
        if queue in subs:
            subs.remove(queue)

    async def _notify(self, job_id: str, event: JobStatus | JobResult) -> None:
        for queue in self._subscribers.get(job_id, []):
            await queue.put(event)

    async def update_status(
        self, job_id: str, step: PipelineStep, detail: str = ""
    ) -> None:
        status = JobStatus(job_id=job_id, step=step, detail=detail)
        await mongo.db.jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": {"step": step.value, "detail": detail}}},
        )
        await self._notify(job_id, status)

    async def set_result(self, job_id: str, result: JobResult) -> None:
        step = PipelineStep.done if result.error is None else PipelineStep.failed
        status = JobStatus(
            job_id=job_id,
            step=step,
            detail=result.error or "",
        )
        await mongo.db.jobs.update_one(
            {"_id": job_id},
            {"$set": {
                "status": {"step": step.value, "detail": result.error or ""},
                "result": result.model_dump(),
            }},
        )
        await self._notify(job_id, status)
        await self._notify(job_id, result)

    async def get_job(self, job_id: str) -> dict | None:
        return await mongo.db.jobs.find_one({"_id": job_id})

    async def find_cached_transcript(
        self, video_url: str, language: str, exclude_job_id: str,
    ) -> Transcript | None:
        """Find a saved transcript from a previous job with the same URL and language."""
        doc = await mongo.db.jobs.find_one(
            {
                "_id": {"$ne": exclude_job_id},
                "video_url": video_url,
                "language": language,
                "transcript": {"$ne": None},
            },
            projection={"transcript": 1},
        )
        if doc and doc.get("transcript"):
            return Transcript.model_validate(doc["transcript"])
        return None


job_store = JobStore()


async def run_pipeline(
    job_id: str,
    video_url: str,
    language: str,
    mode: str = "full",
    source_file: Path | None = None,
) -> None:
    """Run the full analysis pipeline for a job.

    mode controls caching:
      - "full": always download + transcribe from scratch
      - "reuse_transcript": find cached transcript, skip download/transcribe

    If source_file is provided, skip download and use it directly.
    """
    audio_path = None
    loop = asyncio.get_running_loop()

    def _progress(step: PipelineStep, detail: str) -> None:
        """Sync callback usable from worker threads."""
        asyncio.run_coroutine_threadsafe(
            job_store.update_status(job_id, step, detail), loop
        )

    try:
        if mode == "reuse_transcript":
            cached = await job_store.find_cached_transcript(video_url, language, job_id)
            if cached is not None:
                transcript = cached
                await mongo.db.jobs.update_one(
                    {"_id": job_id},
                    {"$set": {"transcript": transcript.model_dump()}},
                )
                await job_store.update_status(
                    job_id, PipelineStep.transcribing,
                    f"Reusing cached transcript ({len(transcript.utterances)} utterances)",
                )
            else:
                # No cached transcript -- fall back to full pipeline
                mode = "full"

        if mode == "full":
            if source_file is not None:
                # File was uploaded directly -- skip download
                audio_path = source_file
                await job_store.update_status(
                    job_id, PipelineStep.downloading,
                    f"Using uploaded file: {source_file.name}",
                )
            else:
                # Step 1: Download with progress
                await job_store.update_status(job_id, PipelineStep.downloading)
                audio_path = await asyncio.to_thread(
                    extract_audio,
                    video_url,
                    None,
                    lambda detail: _progress(PipelineStep.downloading, detail),
                )

            # Step 2: Transcribe (no progress from ElevenLabs API)
            await job_store.update_status(
                job_id, PipelineStep.transcribing,
                "Sending audio to ElevenLabs (no progress available)...",
            )
            transcript = await asyncio.to_thread(transcribe, audio_path, language)
            await mongo.db.jobs.update_one(
                {"_id": job_id},
                {"$set": {"transcript": transcript.model_dump()}},
            )
            await job_store.update_status(
                job_id, PipelineStep.transcribing,
                f"Done -- {len(transcript.utterances)} utterances",
            )

        # Step 3: Split games
        await job_store.update_status(
            job_id, PipelineStep.splitting_games, "Analyzing transcript...",
        )
        split_result = await asyncio.to_thread(split_games, transcript)
        await mongo.db.jobs.update_one(
            {"_id": job_id},
            {"$set": {"split": split_result.model_dump()}},
        )
        n_games = len(split_result.games)
        await job_store.update_status(
            job_id, PipelineStep.splitting_games,
            f"Found {n_games} game(s)",
        )

        # Step 4: Improve diarization per game
        improved_transcripts = []
        for i, game in enumerate(split_result.games, 1):
            await job_store.update_status(
                job_id, PipelineStep.improving_diarization,
                f"Game {i}/{n_games}: identifying players...",
            )
            game_utterances = transcript.utterances[
                game.start_utterance : game.end_utterance
            ]
            improved = await asyncio.to_thread(
                improve_diarization, game_utterances
            )
            n_players = len(
                [m for m in improved.mappings if m.resolved_name != "Judge"]
            )
            await job_store.update_status(
                job_id, PipelineStep.improving_diarization,
                f"Game {i}/{n_games}: found {n_players} players",
            )
            await mongo.db.jobs.update_one(
                {"_id": job_id},
                {"$push": {"diarizations": improved.model_dump()}},
            )
            improved_transcripts.append(improved)

        # Step 5: Generate summaries per game
        game_analyses: list[GameAnalysis] = []
        for i, (game, improved) in enumerate(
            zip(split_result.games, improved_transcripts), 1
        ):
            await job_store.update_status(
                job_id, PipelineStep.generating_summaries,
                f"Game {i}/{n_games}: generating summary...",
            )
            analysis = await asyncio.to_thread(
                generate_game_analysis, improved, game.game_number, language
            )
            await job_store.update_status(
                job_id, PipelineStep.generating_summaries,
                f"Game {i}/{n_games}: done",
            )
            await mongo.db.jobs.update_one(
                {"_id": job_id},
                {"$push": {"analyses": analysis.model_dump()}},
            )
            game_analyses.append(analysis)

        result = JobResult(job_id=job_id, games=game_analyses)
        await job_store.set_result(job_id, result)

    except Exception:
        import traceback

        logger.exception("Pipeline failed for job %s", job_id)
        error_result = JobResult(
            job_id=job_id, error=traceback.format_exc()
        )
        await job_store.set_result(job_id, error_result)

    finally:
        # Cleanup temp audio files
        if audio_path is not None:
            try:
                shutil.rmtree(audio_path.parent, ignore_errors=True)
            except Exception:
                pass
        job_store.running_tasks.pop(job_id, None)
