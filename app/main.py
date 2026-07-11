"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.classifier import load_model
from app.db import get_conn, init_db
from app.retriever import load_index
from app.routers import analyze, queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    logger.info("Initialising database...")
    init_db()
    app.state.db_conn = get_conn()

    logger.info("Loading classification model (this may take a moment)...")
    app.state.model = load_model()
    logger.info("Model loaded.")

    logger.info("Loading embedding index...")
    embeddings, index_metadata = load_index()
    app.state.embeddings = embeddings
    app.state.index_metadata = index_metadata
    if embeddings is None:
        logger.warning(
            "No embedding index found. Retrieval will return empty results. "
            "Run scripts/build_index.py to generate it."
        )
    else:
        logger.info(
            "Embedding index loaded: %d vectors (shape %s).",
            len(index_metadata),
            embeddings.shape,
        )

    yield

    # --- shutdown ---
    app.state.db_conn.close()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Chest X-Ray Triage",
    description="Research prototype — not for clinical use.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data/images/images_normalized", StaticFiles(directory="data/images/images_normalized"), name="data_images")

app.include_router(analyze.router)
app.include_router(queue.router)
