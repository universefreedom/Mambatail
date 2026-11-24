from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import connect
from app.temporal import build_segments


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild segment receipts from an existing runner receipt without model inference.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    labels = json.loads((ROOT / "app/reference_labels.json").read_text(encoding="utf-8"))
    with connect(args.database) as db:
        job = db.execute("SELECT status FROM video_job WHERE job_id=?", (args.job_id,)).fetchone()
        if job is None or job["status"] != "COMPLETED":
            raise SystemExit("job must exist and be COMPLETED")
        db.executemany("UPDATE reference_case SET reference_label=? WHERE case_id=?", [(label, case_id) for case_id, label in labels.items()])
        rows = db.execute("SELECT case_id,source_id,reference_label FROM reference_case").fetchall()
        segments = build_segments(payload, {row["case_id"]: dict(row) for row in rows})
        db.execute("DELETE FROM video_segment WHERE job_id=?", (args.job_id,))
        timestamp = datetime.now(UTC).isoformat()
        db.executemany("INSERT INTO video_segment VALUES (?,?,?,?)", [(args.job_id, item["segment_id"], json.dumps(item), timestamp) for item in segments])
    print(json.dumps({"job_id": args.job_id, "segments": len(segments), "clip_sampled": sum(x["clip_encoded_frames"] for x in segments), "rule_version": segments[0]["fuzzy_observation"]["rule_version"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
