from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.database import connect
from app.settings import Settings


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


class VideoWorker:
    """One durable SQLite-claimed CPU worker; never runs inference in an HTTP request."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.settings.worker_enabled or self._thread:
            return
        self._recover_interrupted()
        self._thread = threading.Thread(target=self._loop, name="mambatail-video-worker", daemon=True)
        self._thread.start()

    def _recover_interrupted(self) -> None:
        with connect(self.settings.database_path) as db:
            db.execute("UPDATE video_job SET status='FAILED',error_code='WORKER_RESTART_INTERRUPTED',finished_at=? WHERE status NOT IN ('QUEUED','COMPLETED','FAILED')", (now(),))

    def _loop(self) -> None:
        while not self._stop.wait(0.5):
            self.run_once()

    def run_once(self) -> bool:
        with connect(self.settings.database_path) as db:
            row = db.execute("SELECT * FROM video_job WHERE status='QUEUED' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return False
            claimed = db.execute("UPDATE video_job SET status='VALIDATING',started_at=? WHERE job_id=? AND status='QUEUED'", (now(), row["job_id"])).rowcount
        if claimed != 1:
            return False
        job_id = row["job_id"]
        started = time.perf_counter()
        try:
            if self.settings.video_runner is None or not self.settings.video_runner.is_file():
                raise RuntimeError("VIDEO_RUNNER_NOT_CONFIGURED")
            output_dir = self.settings.video_runtime_dir / job_id / "artifacts"
            output_dir.mkdir(parents=True, exist_ok=True)
            receipt = output_dir / "runner_receipt.json"
            with connect(self.settings.database_path) as db:
                db.execute("UPDATE video_job SET status='DECODING' WHERE job_id=?", (job_id,))
            completed = subprocess.run(
                [str(self.settings.video_python), str(self.settings.video_runner), "--input", row["input_path"], "--output", str(output_dir), "--receipt", str(receipt)],
                capture_output=True, text=True, timeout=1800,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"RUNNER_FAILED:{completed.stderr[-1000:]}")
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            if payload.get("status") != "PASS":
                raise RuntimeError(payload.get("error_code", "RUNNER_RECEIPT_NOT_PASS"))
            artifact_path = Path(payload["artifact_path"]).resolve()
            artifact_id = str(uuid4())
            with connect(self.settings.database_path) as db:
                db.execute("""UPDATE video_job SET status='COMPLETED',media_metadata=?,model_sha=?,processed_frames=?,detected_frames=?,pose_frames=?,clip_encoded_frames=?,finished_at=?,latency_ms=? WHERE job_id=?""",
                           (json.dumps(payload["input_metadata"]), json.dumps(payload["model_sha"]), payload["processed_frames"], payload["detected_frames"], payload["pose_frames"], payload["clip_encoded_frames"], now(), (time.perf_counter()-started)*1000, job_id))
                db.execute("INSERT INTO video_artifact VALUES (?,?,?,?,?,?,?,?)", (artifact_id, job_id, "ANNOTATED_MP4", str(artifact_path), sha256(artifact_path), artifact_path.stat().st_size, json.dumps(payload["artifact_metadata"]), now()))
        except Exception as exc:
            with connect(self.settings.database_path) as db:
                db.execute("UPDATE video_job SET status='FAILED',error_code=?,finished_at=?,latency_ms=? WHERE job_id=?", (str(exc)[:1500], now(), (time.perf_counter()-started)*1000, job_id))
        return True

