"""API routes for the mafia game analyzer."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.auth import UserInfo, require_auth
from backend.api.games import game_store, run_pipeline, run_reanalysis
from backend import mongo
from backend.models import GameAnalysis, GameResult, GameStatus, InterestSubmission, PipelineStep

router = APIRouter()


class CreateGameResponse(BaseModel):
    game_id: str


class GameListItem(BaseModel):
    game_id: str
    source_filename: str | None
    language: str
    created_at: str
    status: str


@router.post("/interest")
async def submit_interest(submission: InterestSubmission):
    doc = submission.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    await mongo.db.interests.insert_one(doc)
    return {"ok": True}


@router.get("/interests", response_model=list[InterestSubmission])
async def list_interests(_user: UserInfo = Depends(require_auth)):
    docs = await mongo.db.interests.find().to_list(None)
    return [InterestSubmission.model_validate(doc) for doc in docs]


@router.get("/games", response_model=list[GameListItem])
async def list_games(_user: UserInfo = Depends(require_auth)):
    docs = await mongo.db.games.find(
        {},
        projection={"source_filename": 1, "language": 1, "created_at": 1, "upload_status": 1},
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
                source_filename=doc.get("source_filename"),
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
    game_context: str = Form(""),
    model: str = Form("claude-sonnet-4-6"),
    _user: UserInfo = Depends(require_auth),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    game_id = await game_store.create_game(
        language=language,
        source_filename=file.filename,
        game_context=game_context,
    )

    tmp_dir = tempfile.mkdtemp()
    dest = Path(tmp_dir) / file.filename
    contents = await file.read()
    dest.write_bytes(contents)

    task = asyncio.create_task(
        run_pipeline(game_id, language, source_file=dest, game_context=game_context, model=model)
    )
    game_store.running_tasks[game_id] = task
    return CreateGameResponse(game_id=game_id)


class ReanalyzeRequest(BaseModel):
    game_context: str = ""
    model: str = "claude-sonnet-4-6"


@router.post("/games/{game_id}/reanalyze", response_model=CreateGameResponse)
async def reanalyze_game(
    game_id: str,
    body: ReanalyzeRequest,
    _user: UserInfo = Depends(require_auth),
):
    doc = await game_store.get_game(game_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if not doc.get("transcript") or not doc.get("diarization"):
        raise HTTPException(
            status_code=400,
            detail="Game must have transcript and diarization before re-analysis",
        )

    await mongo.db.games.update_one(
        {"_id": game_id}, {"$set": {"game_context": body.game_context}}
    )

    task = asyncio.create_task(
        run_reanalysis(game_id, doc["language"], game_context=body.game_context, model=body.model)
    )
    game_store.running_tasks[game_id] = task
    return CreateGameResponse(game_id=game_id)


@router.get("/games/{game_id}/events")
async def game_events(game_id: str, _user: UserInfo = Depends(require_auth)):
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
async def get_game(game_id: str, _user: UserInfo = Depends(require_auth)):
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
