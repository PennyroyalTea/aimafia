"""API routes for the mafia game analyzer."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from mafia_analyzer.api.jobs import job_store, run_pipeline
from mafia_analyzer.models import JobResult, JobStatus

router = APIRouter()


class SubmitJobRequest(BaseModel):
    video_url: str
    language: str = "ru"


class SubmitJobResponse(BaseModel):
    job_id: str


class JobListItem(BaseModel):
    job_id: str
    video_url: str
    language: str
    created_at: str
    status: str


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


@router.post("/jobs", response_model=SubmitJobResponse)
async def submit_job(req: SubmitJobRequest):
    job_id = job_store.create_job(req.video_url, req.language)
    task = asyncio.create_task(run_pipeline(job_id, req.video_url, req.language))
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
