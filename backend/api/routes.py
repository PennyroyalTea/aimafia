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

from backend.api.jobs import job_store, run_pipeline
from backend.db import db
from backend.models import GameAnalysis, InterestSubmission, JobResult, JobStatus, PipelineStep

router = APIRouter()


class SubmitJobRequest(BaseModel):
    video_url: str
    language: str = "ru"
    mode: Literal["full", "reuse_transcript", "reuse_result"] = "full"


class SubmitJobResponse(BaseModel):
    job_id: str


class JobListItem(BaseModel):
    job_id: str
    video_url: str
    language: str
    created_at: str
    status: str


class UrlMatch(BaseModel):
    job_id: str
    language: str
    created_at: str
    has_transcript: bool
    has_result: bool


@router.post("/interest")
async def submit_interest(submission: InterestSubmission):
    doc = submission.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    await db.interests.insert_one(doc)
    return {"ok": True}


@router.get("/interests", response_model=list[InterestSubmission])
async def list_interests():
    docs = await db.interests.find().to_list(None)
    return [InterestSubmission.model_validate(doc) for doc in docs]


@router.get("/check-url", response_model=list[UrlMatch])
async def check_url(url: str = Query(...), language: str = Query("ru")):
    docs = await db.jobs.find(
        {
            "video_url": url,
            "status.step": {"$in": [PipelineStep.done.value, PipelineStep.failed.value]},
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
                job_id=doc["_id"],
                language=doc["language"],
                created_at=created_str,
                has_transcript=doc.get("transcript") is not None,
                has_result=doc.get("result") is not None and doc["result"].get("error") is None,
            )
        )
    return matches


@router.get("/jobs", response_model=list[JobListItem])
async def list_jobs():
    docs = await db.jobs.find(
        {},
        projection={"video_url": 1, "language": 1, "created_at": 1, "status": 1},
    ).to_list(None)
    items = []
    for doc in docs:
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_str = created_at.isoformat()
        else:
            created_str = str(created_at) if created_at else ""
        items.append(
            JobListItem(
                job_id=doc["_id"],
                video_url=doc["video_url"],
                language=doc["language"],
                created_at=created_str,
                status=doc["status"]["step"],
            )
        )
    return items


@router.post("/upload", response_model=SubmitJobResponse)
async def upload_file(
    file: UploadFile,
    language: str = Form("ru"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    job_id = await job_store.create_job(file.filename, language)

    tmp_dir = tempfile.mkdtemp()
    dest = Path(tmp_dir) / file.filename
    contents = await file.read()
    dest.write_bytes(contents)

    task = asyncio.create_task(
        run_pipeline(job_id, file.filename, language, source_file=dest)
    )
    job_store.running_tasks[job_id] = task
    return SubmitJobResponse(job_id=job_id)


@router.post("/jobs", response_model=SubmitJobResponse)
async def submit_job(req: SubmitJobRequest):
    if req.mode == "reuse_result":
        # Find a completed job with the same URL and return its job_id directly
        doc = await db.jobs.find_one(
            {
                "video_url": req.video_url,
                "language": req.language,
                "result": {"$ne": None},
                "result.error": None,
            },
            projection={"_id": 1},
        )
        if doc:
            return SubmitJobResponse(job_id=doc["_id"])
        # No matching result found -- fall through to full run
        req.mode = "full"

    job_id = await job_store.create_job(req.video_url, req.language)
    task = asyncio.create_task(
        run_pipeline(job_id, req.video_url, req.language, mode=req.mode)
    )
    job_store.running_tasks[job_id] = task
    return SubmitJobResponse(job_id=job_id)


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    if await job_store.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        queue = await job_store.subscribe(job_id)
        try:
            while True:
                event = await queue.get()
                if isinstance(event, JobStatus):
                    yield {
                        "event": "status",
                        "data": event.model_dump_json(),
                    }
                    if event.step in ("done", "failed"):
                        # Keep going -- the result event follows
                        continue
                elif isinstance(event, JobResult):
                    yield {
                        "event": "result",
                        "data": event.model_dump_json(),
                    }
                    return
        finally:
            job_store.unsubscribe(job_id, queue)

    return EventSourceResponse(event_generator())


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    doc = await job_store.get_job(job_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Job not found")

    status = JobStatus(
        job_id=job_id,
        step=PipelineStep(doc["status"]["step"]),
        detail=doc["status"].get("detail", ""),
    )
    response: dict = {"status": status.model_dump()}
    if doc.get("result") is not None:
        result = JobResult(
            job_id=job_id,
            games=[GameAnalysis.model_validate(g) for g in doc["result"].get("games", [])],
            error=doc["result"].get("error"),
        )
        response["result"] = result.model_dump()
    return response
