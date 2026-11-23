from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.database import connect, initialize
from app.gallery import FrozenGallery
from app.settings import Settings, load_settings
from app.video_service import VideoWorker, sha256


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
    worker = VideoWorker(settings)

    @app.on_event("startup")
    def start_video_worker() -> None:
        worker.start()

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        started = time.perf_counter()
        content_length = request.headers.get("content-length")
        if request.url.path != "/api/v1/videos" and content_length and int(content_length) > 4096:
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
                "video_e2e": "FRAME_ONLY_PIPELINE_AVAILABLE" if settings.video_runner else "VIDEO_RUNNER_NOT_CONFIGURED"}

    @app.post("/api/v1/videos", status_code=202)
    async def upload_video(response: Response, file: UploadFile = File(...), x_owner_id: str | None = Header(default=None)) -> dict:
        if not x_owner_id or len(x_owner_id) > 80:
            raise HTTPException(401, "owner header required")
        original = Path(file.filename or "").name
        if original != (file.filename or "") or not original.lower().endswith(".mp4"):
            raise HTTPException(415, "safe .mp4 filename required")
        job_id = str(uuid4())
        job_dir = settings.video_runtime_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        partial = job_dir / "input.part"
        size = 0
        with partial.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_video_bytes:
                    raise HTTPException(413, "video exceeds streaming byte limit")
                stream.write(chunk)
        if size < 12:
            raise HTTPException(415, "empty or invalid MP4")
        with partial.open("rb") as stream:
            header = stream.read(12)
        if b"ftyp" not in header:
            raise HTTPException(415, "MP4 container signature required")
        input_path = job_dir / "input.mp4"
        partial.replace(input_path)
        digest = sha256(input_path)
        with connect(settings.database_path) as db:
            db.execute("""INSERT INTO video_job(job_id,owner_id,original_filename,input_path,input_sha256,input_size,source_scope,pipeline_version,status,created_at) VALUES(?,?,?,?,?,?,?,'REAL_VIDEO_FRAME_ONLY_V1','QUEUED',?)""",
                       (job_id, x_owner_id, original, str(input_path.resolve()), digest, size, "USER_AUTHORIZED_LOCAL_ONLY", utc_now()))
        response.set_cookie("mambatail_owner", x_owner_id, httponly=True, samesite="strict")
        return {"job_id": job_id, "status": "QUEUED", "input_sha256": digest, "input_size": size}

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str, x_owner_id: str | None = Header(default=None)) -> dict:
        with connect(settings.database_path) as db:
            row = db.execute("SELECT * FROM video_job WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "job not found")
        if not x_owner_id or row["owner_id"] != x_owner_id:
            raise HTTPException(403, "owner authorization required")
        result = dict(row)
        result.pop("input_path", None)
        return result

    @app.get("/api/v1/jobs/{job_id}/results")
    def get_results(job_id: str, x_owner_id: str | None = Header(default=None)) -> dict:
        with connect(settings.database_path) as db:
            job = db.execute("SELECT owner_id,status,input_sha256 FROM video_job WHERE job_id=?", (job_id,)).fetchone()
            artifacts = db.execute("SELECT artifact_id,kind,sha256,byte_size,media_metadata FROM video_artifact WHERE job_id=?", (job_id,)).fetchall()
        if job is None:
            raise HTTPException(404, "job not found")
        if not x_owner_id or job["owner_id"] != x_owner_id:
            raise HTTPException(403, "owner authorization required")
        return {"job_id": job_id, "status": job["status"], "input_sha256": job["input_sha256"], "behavior_status": "UNKNOWN", "temporal_ema": "DISABLED", "track_id": "UNVERIFIED", "artifacts": [dict(x) for x in artifacts]}

    @app.get("/api/v1/jobs/{job_id}/artifacts/{artifact_id}")
    def get_artifact(job_id: str, artifact_id: str, request: Request, x_owner_id: str | None = Header(default=None)) -> FileResponse:
        with connect(settings.database_path) as db:
            row = db.execute("""SELECT a.path,j.owner_id,j.status FROM video_artifact a JOIN video_job j ON j.job_id=a.job_id WHERE a.job_id=? AND a.artifact_id=?""", (job_id, artifact_id)).fetchone()
        if row is None:
            raise HTTPException(404, "artifact not found")
        owner = x_owner_id or request.cookies.get("mambatail_owner")
        if not owner or row["owner_id"] != owner:
            raise HTTPException(403, "owner authorization required")
        if row["status"] != "COMPLETED":
            raise HTTPException(409, "artifact is not complete")
        return FileResponse(row["path"], media_type="video/mp4", filename="mambatail-annotated.mp4")

    return app
