from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class CaseMeta:
    case_id: str
    source_id: int
    shot_id: int


class FrozenGallery:
    def __init__(self, npz_path: Path, audit_csv: Path) -> None:
        if not npz_path.is_file() or not audit_csv.is_file():
            raise FileNotFoundError("authorized frozen gallery paths are not configured")
        archive = np.load(npz_path, allow_pickle=False)
        all_ids = [str(value) for value in archive["case_ids"]]
        all_vectors = np.asarray(archive["embeddings"], dtype=np.float32)
        by_id = {case_id: all_vectors[index] for index, case_id in enumerate(all_ids)}
        metadata: list[CaseMeta] = []
        with audit_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if (row.get("split_role") or row.get("role")) != "gallery":
                    continue
                metadata.append(CaseMeta(row["case_id"], int(row["source_video_id"]), int(row["shot_id"])))
        if len(metadata) != 51:
            raise ValueError(f"expected 51 gallery cases, observed {len(metadata)}")
        missing = [item.case_id for item in metadata if item.case_id not in by_id]
        if missing:
            raise ValueError(f"gallery vectors missing for {len(missing)} cases")
        self.metadata = metadata
        self.case_ids = [item.case_id for item in metadata]
        matrix = np.stack([by_id[case_id] for case_id in self.case_ids])
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if np.any(norms <= 0):
            raise ValueError("gallery contains zero-norm vectors")
        self.vectors = matrix / norms
        self.index = {case_id: index for index, case_id in enumerate(self.case_ids)}

    def search(self, query_case_id: str, top_k: int) -> list[tuple[str, float]]:
        try:
            query = self.vectors[self.index[query_case_id]]
        except KeyError as exc:
            raise KeyError("query case is not in the frozen gallery") from exc
        scores = self.vectors @ query
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [(self.case_ids[int(index)], float(scores[int(index)])) for index in order]
