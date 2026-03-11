"""FastAPI application for the mafia game analyzer."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mafia_analyzer.api.jobs import job_store
from mafia_analyzer.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    job_store.load_from_disk()
    yield
    # Shutdown: cancel any running jobs
    for task in job_store.running_tasks.values():
        task.cancel()


app = FastAPI(title="Mafia Game Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
