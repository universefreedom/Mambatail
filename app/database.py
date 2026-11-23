from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS reference_case (
  case_id TEXT PRIMARY KEY,
  source_id INTEGER NOT NULL,
  shot_id INTEGER NOT NULL,
  evidence_tier TEXT NOT NULL,
  reference_label TEXT NOT NULL,
  embedding_ref TEXT NOT NULL,
  provenance_ref TEXT NOT NULL,
  version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_request (
  request_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  retrieval_method TEXT NOT NULL,
  result_count INTEGER NOT NULL,
  scope TEXT NOT NULL,
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_result (
  request_id TEXT NOT NULL REFERENCES search_request(request_id) ON DELETE CASCADE,
  case_id TEXT NOT NULL REFERENCES reference_case(case_id),
  rank INTEGER NOT NULL,
  raw_score REAL NOT NULL,
  score_semantics TEXT NOT NULL,
  PRIMARY KEY (request_id, rank)
);
CREATE TABLE IF NOT EXISTS system_event (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  non_sensitive_details TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS video_job (
  job_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  input_path TEXT NOT NULL,
  input_sha256 TEXT NOT NULL,
  input_size INTEGER NOT NULL,
  media_metadata TEXT,
  source_scope TEXT NOT NULL,
  model_sha TEXT,
  pipeline_version TEXT NOT NULL,
  status TEXT NOT NULL,
  processed_frames INTEGER NOT NULL DEFAULT 0,
  detected_frames INTEGER NOT NULL DEFAULT 0,
  pose_frames INTEGER NOT NULL DEFAULT 0,
  clip_encoded_frames INTEGER NOT NULL DEFAULT 0,
  error_code TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  latency_ms REAL
);
CREATE TABLE IF NOT EXISTS video_artifact (
  artifact_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES video_job(job_id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  media_metadata TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_video_job_status ON video_job(status, created_at);
"""


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript(SCHEMA)


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
