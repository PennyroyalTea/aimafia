"""API routes for the mafia game analyzer."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.games import game_store, run_pipeline
from backend import mongo
from backend.models import GameAnalysis, GameResult, GameStatus, InterestSubmission, PipelineStep

router = APIRouter()


class CreateGameRequest(BaseModel):
    video_url: str
    language: str = "ru"
    mode: Literal["full", "reuse_transcript", "reuse_result"] = "full"


class CreateGameResponse(BaseModel):
    game_id: str


class GameListItem(BaseModel):
    game_id: str
    video_url: str | None
    language: str
    created_at: str
    status: str


class UrlMatch(BaseModel):
    game_id: str
    language: str
    created_at: str
    has_transcript: bool
    has_result: bool


@router.post("/interest")
async def submit_interest(submission: InterestSubmission):
    doc = submission.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    await mongo.db.interests.insert_one(doc)
    return {"ok": True}


@router.get("/interests", response_model=list[InterestSubmission])
async def list_interests():
    docs = await mongo.db.interests.find().to_list(None)
    return [InterestSubmission.model_validate(doc) for doc in docs]


@router.get("/check-url", response_model=list[UrlMatch])
async def check_url(url: str = Query(...), language: str = Query("ru")):
    docs = await mongo.db.games.find(
        {
            "video_url": url,
            "upload_status.step": {"$in": [PipelineStep.done.value, PipelineStep.failed.value]},
        },
    ).to_list(None)
    matches = []
    for doc in docs:
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_str = created_at.isoformat()
        else:
            created_str = str(created_at) if created_at else ""
        matches.append(
            UrlMatch(
                game_id=doc["_id"],
                language=doc["language"],
                created_at=created_str,
                has_transcript=doc.get("transcript") is not None,
                has_result=doc.get("analysis") is not None,
            )
        )
    return matches


@router.get("/games", response_model=list[GameListItem])
async def list_games():
    docs = await mongo.db.games.find(
        {},
        projection={"video_url": 1, "source_filename": 1, "language": 1, "created_at": 1, "upload_status": 1},
    ).to_list(None)
    items = []
    for doc in docs:
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_str = created_at.isoformat()
        else:
            created_str = str(created_at) if created_at else ""
        items.append(
            GameListItem(
                game_id=doc["_id"],
                video_url=doc.get("video_url"),
                language=doc["language"],
                created_at=created_str,
                status=doc["upload_status"]["step"],
            )
        )
    return items


@router.post("/games/upload", response_model=CreateGameResponse)
async def upload_file(
    file: UploadFile,
    language: str = Form("ru"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    game_id = await game_store.create_game(
        video_url=None,
        language=language,
        source_filename=file.filename,
    )

    tmp_dir = tempfile.mkdtemp()
    dest = Path(tmp_dir) / file.filename
    contents = await file.read()
    dest.write_bytes(contents)

    task = asyncio.create_task(
        run_pipeline(game_id, file.filename, language, source_file=dest)
    )
    game_store.running_tasks[game_id] = task
    return CreateGameResponse(game_id=game_id)


@router.post("/games", response_model=CreateGameResponse)
async def create_game(req: CreateGameRequest):
    if req.mode == "reuse_result":
        # Find a completed game with the same URL and return its game_id directly
        doc = await mongo.db.games.find_one(
            {
                "video_url": req.video_url,
                "language": req.language,
                "analysis": {"$ne": None},
                "error": None,
            },
            projection={"_id": 1},
        )
        if doc:
            return CreateGameResponse(game_id=doc["_id"])
        # No matching result found -- fall through to full run
        req.mode = "full"

    game_id = await game_store.create_game(video_url=req.video_url, language=req.language)
    task = asyncio.create_task(
        run_pipeline(game_id, req.video_url, req.language, mode=req.mode)
    )
    game_store.running_tasks[game_id] = task
    return CreateGameResponse(game_id=game_id)


@router.get("/games/{game_id}/events")
async def game_events(game_id: str):
    if await game_store.get_game(game_id) is None:
        raise HTTPException(status_code=404, detail="Game not found")

    async def event_generator():
        queue = await game_store.subscribe(game_id)
        try:
            while True:
                event = await queue.get()
                if isinstance(event, GameStatus):
                    yield {
                        "event": "status",
                        "data": event.model_dump_json(),
                    }
                    if event.step in (PipelineStep.done, PipelineStep.failed):
                        # Keep going -- the result event follows
                        continue
                elif isinstance(event, GameResult):
                    yield {
                        "event": "result",
                        "data": event.model_dump_json(),
                    }
                    return
        finally:
            game_store.unsubscribe(game_id, queue)

    return EventSourceResponse(event_generator())


@router.get("/games/{game_id}")
async def get_game(game_id: str):
    doc = await game_store.get_game(game_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Game not found")

    status = GameStatus(
        game_id=game_id,
        step=PipelineStep(doc["upload_status"]["step"]),
        detail=doc["upload_status"].get("detail", ""),
    )
    response: dict = {"status": status.model_dump()}
    step = PipelineStep(doc["upload_status"]["step"])
    if step in (PipelineStep.done, PipelineStep.failed):
        analysis = (
            GameAnalysis.model_validate(doc["analysis"])
            if doc.get("analysis")
            else None
        )
        result = GameResult(
            game_id=game_id,
            analysis=analysis,
            error=doc.get("error"),
        )
        response["result"] = result.model_dump()
    return response
