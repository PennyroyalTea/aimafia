"""API routes for the mafia game analyzer."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from mafia_analyzer.api.jobs import _job_dir, job_store, run_pipeline
from mafia_analyzer.models import JobResult, JobStatus, PipelineStep

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


@router.get("/check-url", response_model=list[UrlMatch])
async def check_url(url: str = Query(...), language: str = Query("ru")):
    matches = []
    for job in job_store._jobs.values():
        if job["video_url"] != url:
            continue
        status: JobStatus = job["status"]
        if status.step not in (PipelineStep.done, PipelineStep.failed):
            continue
        meta = job.get("meta")
        jdir = _job_dir(job["job_id"])
        matches.append(
            UrlMatch(
                job_id=job["job_id"],
                language=job["language"],
                created_at=meta.created_at.isoformat() if meta else "",
                has_transcript=(jdir / "transcript.json").exists(),
                has_result=job["result"] is not None and job["result"].error is None,
            )
        )
    return matches


@router.get("/jobs", response_model=list[JobListItem])
async def list_jobs():
    items = []
    for job in job_store._jobs.values():
        meta = job.get("meta")
        status: JobStatus = job["status"]
        items.append(
            JobListItem(
                job_id=job["job_id"],
                video_url=job["video_url"],
                language=job["language"],
                created_at=meta.created_at.isoformat() if meta else "",
                status=status.step.value,
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

    job_id = job_store.create_job(file.filename, language)
    jdir = _job_dir(job_id)

    dest = jdir / file.filename
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
        for job in job_store._jobs.values():
            if (
                job["video_url"] == req.video_url
                and job["language"] == req.language
                and job["result"] is not None
                and job["result"].error is None
            ):
                return SubmitJobResponse(job_id=job["job_id"])
        # No matching result found -- fall through to full run
        req.mode = "full"

    job_id = job_store.create_job(req.video_url, req.language)
    task = asyncio.create_task(
        run_pipeline(job_id, req.video_url, req.language, mode=req.mode)
    )
    job_store.running_tasks[job_id] = task
    return SubmitJobResponse(job_id=job_id)


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    if job_store.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        queue = job_store.subscribe(job_id)
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
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    response: dict = {"status": job["status"].model_dump()}
    if job["result"] is not None:
        response["result"] = job["result"].model_dump()
    return response
