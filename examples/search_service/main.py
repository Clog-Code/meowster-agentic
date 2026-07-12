"""MeowDoc search service entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from search.routes import router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="MeowDoc Search Service",
    description="Web search and visual search for cat health context",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
