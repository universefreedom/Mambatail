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


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        database_path=Path(os.getenv("MAMBATAIL_DATABASE_PATH", "runtime/portfolio.sqlite3")),
        gallery_npz=Path(os.getenv("MAMBATAIL_GALLERY_NPZ", "")),
        gallery_audit_csv=Path(os.getenv("MAMBATAIL_GALLERY_AUDIT_CSV", "")),
        model_version=os.getenv("MAMBATAIL_MODEL_VERSION", "OPENAI_CLIP_RN50_FROZEN_V50"),
    )
