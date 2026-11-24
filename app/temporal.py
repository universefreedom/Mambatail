from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


RULE_VERSION = "FRAME_OBSERVATION_FUZZY_V1"


def _pose_features(npz_path: Path) -> dict[str, Any]:
    archive = np.load(npz_path)
    skeletons = archive["skeletons"].astype(np.float32)
    boxes = archive["boxes"].astype(np.float32)
    frame_count = skeletons.shape[1]
    selected = []
    valid_ratios = []
    for frame in range(frame_count):
        slot = int(np.argmax(boxes[:, frame, 4]))
        points = skeletons[slot, frame]
        selected.append(points)
        valid_ratios.append(float(np.mean(points[:, 2] > 0.12)))
    changes = []
    for previous, current in zip(selected, selected[1:]):
        valid = (previous[:, 2] > 0.12) & (current[:, 2] > 0.12)
        if not np.any(valid):
            continue
        extent = np.ptp(current[valid, :2], axis=0)
        diagonal = float(np.linalg.norm(extent))
        if diagonal <= 1e-6:
            continue
        displacement = np.linalg.norm(current[valid, :2] - previous[valid, :2], axis=1)
        changes.append(float(np.median(displacement) / diagonal))
    coverage = float(np.mean(valid_ratios)) if valid_ratios else 0.0
    magnitude = float(np.median(changes)) if changes else None
    variation = float(np.std(changes)) if changes else None
    return {
        "valid_joint_ratio": coverage,
        "normalized_pose_change_median": magnitude,
        "normalized_pose_change_std": variation,
        "valid_change_pairs": len(changes),
        "selection_policy": "HIGHEST_DETECTOR_SCORE_SLOT_PER_FRAME",
        "subject_identity_authority": "UNVERIFIED",
    }


def _fuzzy(features: dict[str, Any]) -> dict[str, Any]:
    value = features["normalized_pose_change_median"]
    coverage = features["valid_joint_ratio"]
    missing = []
    if value is None:
        missing.append("normalized_pose_change_median")
    if coverage < 0.5:
        category = "OBSERVATION_INSUFFICIENT"
        explanation = "유효 관절 관측률이 0.5 미만이어서 움직임 수준을 요약하지 않습니다."
    elif value is None:
        category = "OBSERVATION_INSUFFICIENT"
        explanation = "연속 유효 관절 쌍이 없어 포즈 변화량을 계산하지 못했습니다."
    elif value < 0.01:
        category = "MOTION_LOW"
        explanation = "관측 프레임의 정규화 관절 위치 변화 중앙값이 0.01 미만입니다."
    elif value < 0.04:
        category = "MOTION_MODERATE"
        explanation = "관측 프레임의 정규화 관절 위치 변화 중앙값이 0.01 이상 0.04 미만입니다."
    else:
        category = "MOTION_HIGH"
        explanation = "관측 프레임의 정규화 관절 위치 변화 중앙값이 0.04 이상입니다."
    return {
        "rule_id": "MOTION_BY_NORMALIZED_POSE_CHANGE_AND_COVERAGE",
        "rule_version": RULE_VERSION,
        "input_features": features,
        "missing_features": missing,
        "output_category": category,
        "explanation_text": explanation,
        "probability": None,
    }


def build_segments(payload: dict[str, Any], reference_metadata: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    artifact = Path(payload["artifact_path"])
    pose_root = artifact.parent / "prs_ap10k"
    report = json.loads((pose_root / "report.json").read_text(encoding="utf-8"))
    input_fps = float(payload["input_metadata"]["fps"])
    clip_records = payload.get("clip_records", [])
    segments = []
    for window in report["windows"]:
        window_id = int(window["window_id"])
        features = _pose_features(pose_root / f"window_{window_id:04d}_ap10k17.npz")
        start_sec, end_sec = float(window["start_sec"]), float(window["end_sec"])
        candidates = [x for x in clip_records if start_sec <= float(x["frame_index"]) / input_fps <= end_sec + 1e-6]
        record = candidates[0] if candidates else None
        hits = []
        if record:
            for rank, hit in enumerate(record["top5"][:3], 1):
                meta = reference_metadata.get(hit["case_id"], {})
                hits.append({"rank": rank, "case_id": hit["case_id"], "similarity": hit["cosine"], "reference_label": hit.get("reference_label") or meta.get("reference_label"), "source_id": hit.get("source_id", meta.get("source_id")), "label_authority": "SOURCE_MANUAL_REFERENCE_ONLY", "public_image": None})
        fuzzy = _fuzzy(features)
        source_ids = [x["source_id"] for x in hits if x["source_id"] is not None]
        warning = "SOURCE_CONCENTRATION_WARNING" if source_ids and len(set(source_ids)) == 1 else None
        segments.append({
            "segment_id": f"SEG_{window_id:04d}", "start_frame": int(window["start_frame"]), "end_frame": int(window["end_frame"]),
            "start_time_sec": start_sec, "end_time_sec": end_sec, "time_authority": "DECODED_SOURCE_FPS_OBSERVED",
            "subject_identity_authority": "UNVERIFIED", "valid_pose_frames": int(window["detected_frames"]),
            "clip_encoded_frames": 1 if record else 0, "evidence_quality": "OBSERVED_FRAME_FEATURES_IDENTITY_UNVERIFIED",
            "pose_observation": features, "clip_reference_hits": hits,
            "similarity_summary": {"mean_top3_cosine": float(np.mean([x["similarity"] for x in hits])) if hits else None, "semantics": "REFERENCE_SIMILARITY_NOT_BEHAVIOR_PROBABILITY"},
            "fuzzy_observation": fuzzy, "source_warning": warning,
            "review_assistance": f"{fuzzy['explanation_text']} 참고 사례 라벨은 입력 영상의 확정 행동이 아니며 검토용입니다.",
            "behavior_status": "UNKNOWN", "l4": "DISABLED",
            "model_versions": payload["model_sha"], "missing_evidence": ["TRACK_ID_AUTHORITY", "EXPERT_BEHAVIOR_GROUND_TRUTH"] + ([] if hits else ["SEGMENT_CLIP_SAMPLE"]),
        })
    return segments
