from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.database import connect, initialize
from app.gallery import FrozenGallery
from app.settings import Settings, load_settings


class SearchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_case_id: str = Field(pattern=r"^CASE_[0-9A-F]{16}$")
    top_k: int = Field(default=5, ge=1, le=10)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    initialize(settings.database_path)
    gallery = FrozenGallery(settings.gallery_npz, settings.gallery_audit_csv)
    app = FastAPI(title="MambaTail Evidence Portfolio", version="1.0.0")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        started = time.perf_counter()
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 4096:
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Server-Timing"] = f"app;dur={(time.perf_counter()-started)*1000:.3f}"
        return response

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/healthz")
    def healthz() -> dict:
        with connect(settings.database_path) as db:
            count = db.execute("SELECT COUNT(*) FROM reference_case").fetchone()[0]
        return {"status": "ok" if count == 51 else "degraded", "database": "sqlite",
                "reference_cases": count, "gallery_vectors": len(gallery.case_ids)}

    @app.get("/api/v1/cases")
    def cases(limit: int = 12) -> dict:
        limit = max(1, min(limit, 51))
        with connect(settings.database_path) as db:
            rows = db.execute(
                """SELECT case_id,source_id,shot_id,evidence_tier,reference_label,version
                   FROM reference_case ORDER BY case_id LIMIT ?""", (limit,)).fetchall()
        return {"items": [dict(row) for row in rows], "total": 51}

    @app.post("/api/v1/search")
    def search(body: SearchBody) -> dict:
        started = time.perf_counter()
        with connect(settings.database_path) as db:
            query_row = db.execute(
                "SELECT case_id,source_id,shot_id FROM reference_case WHERE case_id=?",
                (body.query_case_id,)).fetchone()
            if query_row is None:
                raise HTTPException(404, "query case not found")
            hits = gallery.search(body.query_case_id, body.top_k)
            placeholders = ",".join("?" for _ in hits)
            metadata = {row["case_id"]: row for row in db.execute(
                f"""SELECT case_id,source_id,shot_id,evidence_tier,reference_label,version
                    FROM reference_case WHERE case_id IN ({placeholders})""",
                [case_id for case_id, _ in hits]).fetchall()}
            request_id, observed_at = str(uuid4()), utc_now()
            db.execute("INSERT INTO search_request VALUES (?,?,?,?,?,?)",
                       (request_id, observed_at, "FROZEN_CLIP_RN50_COSINE", len(hits), "51_GALLERY", "PASS"))
            items = []
            for rank, (case_id, score) in enumerate(hits, start=1):
                row = metadata[case_id]
                db.execute("INSERT INTO search_result VALUES (?,?,?,?,?)",
                           (request_id, case_id, rank, score, "UNCALIBRATED_COSINE_SIMILARITY"))
                items.append({**dict(row), "rank": rank, "similarity_or_distance": score,
                              "metric_type": "COSINE_SIMILARITY", "query_behavior_status": "UNKNOWN"})
            db.execute("INSERT INTO system_event VALUES (?,?,?,?,?)",
                       (str(uuid4()), "SEARCH", "PASS", observed_at,
                        json.dumps({"request_id": request_id, "result_count": len(items)})))
        return {"request_id": request_id, "execution_mode": "CACHED_RETRIEVAL_E2E_PASS",
                "query": dict(query_row), "results": items,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "interpretation": "REFERENCE_SIMILARITY_ONLY_NOT_EXPERT_PROBABILITY"}

    @app.get("/api/v1/system-status")
    def system_status() -> dict:
        return {"service": "MambaTail", "model_version": settings.model_version,
                "scientific_status": "SCIENTIFIC_NO_PROMOTION",
                "protected_research_release": "PUBLIC_RELEASE_BLOCKED",
                "query_behavior_status": "UNKNOWN", "fuzzy_status": "GATED_DESCRIPTIVE_ONLY",
                "fresh_image_inference": "NOT_EXPOSED",
                "video_e2e": "SCOPED_BLOCK_NO_VERIFIED_IDENTITY_AND_PTS"}

    return app
