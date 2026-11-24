from __future__ import annotations

import json
from pathlib import Path

from app.database import connect, initialize
from app.gallery import FrozenGallery
from app.settings import load_settings


def main() -> None:
    settings = load_settings()
    gallery = FrozenGallery(settings.gallery_npz, settings.gallery_audit_csv)
    labels = json.loads((Path(__file__).parent / "reference_labels.json").read_text(encoding="utf-8"))
    initialize(settings.database_path)
    with connect(settings.database_path) as db:
        db.execute("DELETE FROM reference_case")
        db.executemany(
            """INSERT INTO reference_case
               (case_id,source_id,shot_id,evidence_tier,reference_label,
                embedding_ref,provenance_ref,version) VALUES (?,?,?,?,?,?,?,?)""",
            [(item.case_id, item.source_id, item.shot_id, "DERIVED_ONLY_TECHNICAL",
              labels[item.case_id], f"frozen-gallery:{item.case_id}",
              "V50_EXACT_CASE_FRAME_JOIN_AUDIT", settings.model_version)
             for item in gallery.metadata],
        )
    print(f"initialized {len(gallery.metadata)} reference cases at {settings.database_path}")


if __name__ == "__main__":
    main()
