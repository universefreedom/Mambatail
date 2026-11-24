from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_path: Path
    gallery_npz: Path
    gallery_audit_csv: Path
    model_version: str
    video_runtime_dir: Path = Path("runtime/videos")
    video_runner: Path | None = None
    video_python: Path = Path("python")
    max_video_bytes: int = 80 * 1024 * 1024
    worker_enabled: bool = False
    public_upload_enabled: bool = False
    public_showcase_job_id: str | None = None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        database_path=Path(os.getenv("MAMBATAIL_DATABASE_PATH", "runtime/portfolio.sqlite3")),
        gallery_npz=Path(os.getenv("MAMBATAIL_GALLERY_NPZ", "")),
        gallery_audit_csv=Path(os.getenv("MAMBATAIL_GALLERY_AUDIT_CSV", "")),
        model_version=os.getenv("MAMBATAIL_MODEL_VERSION", "OPENAI_CLIP_RN50_FROZEN_V50"),
        video_runtime_dir=Path(os.getenv("MAMBATAIL_VIDEO_RUNTIME_DIR", "runtime/videos")),
        video_runner=Path(os.environ["MAMBATAIL_VIDEO_RUNNER"]) if os.getenv("MAMBATAIL_VIDEO_RUNNER") else None,
        video_python=Path(os.getenv("MAMBATAIL_VIDEO_PYTHON", "python")),
        max_video_bytes=int(os.getenv("MAMBATAIL_MAX_VIDEO_BYTES", str(80 * 1024 * 1024))),
        worker_enabled=os.getenv("MAMBATAIL_VIDEO_WORKER", "0") == "1",
        public_upload_enabled=os.getenv("MAMBATAIL_PUBLIC_UPLOAD_ENABLED", "0") == "1",
        public_showcase_job_id=os.getenv("MAMBATAIL_PUBLIC_SHOWCASE_JOB_ID") or None,
    )
