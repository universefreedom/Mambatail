from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.database import connect, initialize
from app.gallery import FrozenGallery
from app.main import create_app
from app.settings import Settings


def fixture_settings(tmp_path: Path) -> Settings:
    case_ids = np.array([f"CASE_{index:016X}" for index in range(51)])
    vectors = np.eye(51, 1024, dtype=np.float32)
    npz = tmp_path / "gallery.npz"
    np.savez(npz, case_ids=case_ids, embeddings=vectors)
    audit = tmp_path / "audit.csv"
    with audit.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case_id", "role", "source_video_id", "shot_id"])
        writer.writeheader()
        for index, case_id in enumerate(case_ids):
            writer.writerow({"case_id": case_id, "role": "gallery", "source_video_id": index // 3, "shot_id": index})
    return Settings(tmp_path / "portfolio.sqlite3", npz, audit, "TEST_MODEL")


def seed(settings: Settings) -> None:
    gallery = FrozenGallery(settings.gallery_npz, settings.gallery_audit_csv)
    initialize(settings.database_path)
    with connect(settings.database_path) as db:
        db.executemany(
            "INSERT INTO reference_case VALUES (?,?,?,?,?,?,?,?)",
            [(x.case_id, x.source_id, x.shot_id, "DERIVED_ONLY_TECHNICAL",
              "SOURCE_MANUAL_REFERENCE_ONLY", x.case_id, "TEST", settings.model_version)
             for x in gallery.metadata],
        )


def test_browser_api_db_gallery_e2e(tmp_path: Path) -> None:
    settings = fixture_settings(tmp_path)
    seed(settings)
    client = TestClient(create_app(settings))
    assert client.get("/").status_code == 200
    assert client.get("/healthz").json()["reference_cases"] == 51
    cases = client.get("/api/v1/cases").json()
    response = client.post("/api/v1/search", json={"query_case_id": cases["items"][0]["case_id"], "top_k": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_mode"] == "CACHED_RETRIEVAL_E2E_PASS"
    assert len(payload["results"]) == 5
    assert payload["results"][0]["similarity_or_distance"] == 1.0
    assert payload["results"][0]["query_behavior_status"] == "UNKNOWN"


def test_input_guards(tmp_path: Path) -> None:
    settings = fixture_settings(tmp_path)
    seed(settings)
    client = TestClient(create_app(settings))
    assert client.post("/api/v1/search", json={"query_case_id": "bad", "top_k": 5}).status_code == 422
    assert client.post("/api/v1/search", json={"query_case_id": "CASE_FFFFFFFFFFFFFFFF", "top_k": 5}).status_code == 404
    assert client.post("/api/v1/search", json={"query_case_id": "CASE_0000000000000000", "top_k": 99}).status_code == 422


def test_video_upload_streaming_guards_and_owner_scope(tmp_path: Path) -> None:
    settings = fixture_settings(tmp_path)
    settings = Settings(settings.database_path, settings.gallery_npz, settings.gallery_audit_csv,
                        settings.model_version, tmp_path / "videos", None, Path("python"), 64, False, True)
    seed(settings)
    client = TestClient(create_app(settings))
    assert client.post("/api/v1/videos", files={"file": ("x.mp4", b"\x00\x00\x00\x18ftypisomDATA", "video/mp4")}).status_code == 401
    headers = {"X-Owner-ID": "owner-a"}
    assert client.post("/api/v1/videos", headers=headers, files={"file": ("../x.mp4", b"\x00\x00\x00\x18ftypisomDATA", "video/mp4")}).status_code == 415
    assert client.post("/api/v1/videos", headers=headers, files={"file": ("x.mp4.exe", b"\x00\x00\x00\x18ftypisomDATA", "video/mp4")}).status_code == 415
    assert client.post("/api/v1/videos", headers=headers, files={"file": ("x.mp4", b"not-an-mp4-container", "video/mp4")}).status_code == 415
    assert client.post("/api/v1/videos", headers=headers, files={"file": ("x.mp4", b"\x00\x00\x00\x18ftypisom" + b"x" * 100, "video/mp4")}).status_code == 413
    accepted = client.post("/api/v1/videos", headers=headers, files={"file": ("x.mp4", b"\x00\x00\x00\x18ftypisomDATA", "video/mp4")})
    assert accepted.status_code == 202
    job_id = accepted.json()["job_id"]
    assert client.get(f"/api/v1/jobs/{job_id}", headers={"X-Owner-ID": "owner-b"}).status_code == 403
    assert client.get(f"/api/v1/jobs/{job_id}/results", headers=headers).json()["status"] == "QUEUED"
