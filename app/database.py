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
