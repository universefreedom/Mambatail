from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


RULE_VERSION = "FRAME_OBSERVATION_FUZZY_V2_IDENTITY_GATED"


def _ramp_down(value: float, full_until: float, zero_at: float) -> float:
    if value <= full_until:
        return 1.0
    if value >= zero_at:
        return 0.0
    return float((zero_at - value) / (zero_at - full_until))


def _triangle(value: float, left: float, peak: float, right: float) -> float:
    if value <= left or value >= right:
        return 0.0
    if value == peak:
        return 1.0
    if value < peak:
        return float((value - left) / (peak - left))
    return float((right - value) / (right - peak))


def _ramp_up(value: float, zero_until: float, full_at: float) -> float:
    if value <= zero_until:
        return 0.0
    if value >= full_at:
        return 1.0
    return float((value - zero_until) / (full_at - zero_until))


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
    representative = selected[len(selected) // 2] if selected else None
    thumbnail = None
    if representative is not None:
        valid = representative[:, 2] > 0.12
        if np.any(valid):
            xs, ys = representative[valid, 0], representative[valid, 1]
            width, height = max(float(np.ptp(xs)), 1e-6), max(float(np.ptp(ys)), 1e-6)
            scale = max(width, height)
            min_x, min_y = float(np.min(xs)), float(np.min(ys))
            thumbnail = [
                {"x": float((point[0] - min_x) / scale), "y": float((point[1] - min_y) / scale), "confidence": float(point[2])}
                if point[2] > 0.12 else {"x": None, "y": None, "confidence": float(point[2])}
                for point in representative
            ]
    return {
        "valid_joint_ratio": coverage,
        "normalized_pose_change_median": magnitude,
        "normalized_pose_change_std": variation,
        "valid_change_pairs": len(changes),
        "selection_policy": "HIGHEST_DETECTOR_SCORE_SLOT_PER_FRAME",
        "subject_identity_authority": "UNVERIFIED",
        "query_pose_thumbnail": {"schema": "AP10K_NATIVE17", "coordinates": thumbnail, "authority": "QUERY_OBSERVATION_VISUALIZATION", "normalization": "VALID_JOINT_BBOX_MAX_AXIS"} if thumbnail else None,
    }


def _fuzzy(features: dict[str, Any]) -> dict[str, Any]:
    value = features["normalized_pose_change_median"]
    coverage = features["valid_joint_ratio"]
    missing = []
    identity = features.get("subject_identity_authority", "UNVERIFIED")
    if value is None:
        missing.append("normalized_pose_change_median")
    memberships = {
        "motion_low": None if value is None else _ramp_down(value, 0.01, 0.04),
        "motion_moderate": None if value is None else _triangle(value, 0.01, 0.04, 0.08),
        "motion_high": None if value is None else _ramp_up(value, 0.04, 0.08),
        "coverage_sufficient": _ramp_up(coverage, 0.35, 0.75),
    }
    if coverage < 0.5:
        category = "OBSERVATION_INSUFFICIENT"
        explanation = "유효 관절 관측률이 0.5 미만이어서 움직임 수준을 요약하지 않습니다."
    elif value is None:
        category = "OBSERVATION_INSUFFICIENT"
        explanation = "연속 유효 관절 쌍이 없어 포즈 변화량을 계산하지 못했습니다."
    else:
        category = max(("POSE_VARIATION_LOW", "POSE_VARIATION_MODERATE", "POSE_VARIATION_HIGH"), key=lambda key: memberships[key.replace("POSE_VARIATION_", "motion_").lower()])
        explanation = "실제 관절 좌표 변화량에 기술 설계 소속함수를 적용한 관측 변화 범주입니다. 행동 확률이 아니며 전문가가 원영상과 함께 검토하는 보조 계측입니다."
    return {
        "rule_id": "POSE_VARIATION_MEMBERSHIP_WITH_COVERAGE_AND_IDENTITY_GATE",
        "rule_version": RULE_VERSION,
        "membership_design": {
            "motion_low": "left_shoulder(full<=0.01, zero>=0.04)",
            "motion_moderate": "triangle(0.01, 0.04, 0.08)",
            "motion_high": "right_shoulder(zero<=0.04, full>=0.08)",
            "coverage_sufficient": "right_shoulder(zero<=0.35, full>=0.75)",
            "authority": "TECHNICAL_DESIGN_NOT_EXPERT_VALIDATED",
        },
        "memberships": memberships,
        "input_features": features,
        "missing_features": missing,
        "output_category": category,
        "explanation_text": explanation,
        "probability": None,
        "interpretation_scope": "FRAME_LEVEL_POSE_VARIATION_MEASUREMENT" if identity != "VERIFIED_TRACK" else "VERIFIED_TRACK_POSE_VARIATION_MEASUREMENT",
        "identity_caveat": "프레임별 최고 검출 점수 슬롯이며 동일 개체 추적은 검증되지 않았습니다." if identity != "VERIFIED_TRACK" else None,
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
        candidates = [x for x in clip_records if start_sec <= float(x["frame_index"]) / input_fps < end_sec]
        record = candidates[0] if candidates else None
        hits = []
        if record:
            for rank, hit in enumerate(record["top5"][:3], 1):
                meta = reference_metadata.get(hit["case_id"], {})
                hits.append({"rank": rank, "case_id": hit["case_id"], "similarity": hit["cosine"], "reference_label": hit.get("reference_label") or meta.get("reference_label"), "source_id": hit.get("source_id", meta.get("source_id")), "sample_frame_index": int(record["frame_index"]), "label_authority": "SOURCE_MANUAL_REFERENCE_ONLY", "source_warning": "REFERENCE_SIMILARITY_NOT_BEHAVIOR_TRUTH", "evidence_tier": "RESEARCH_REFERENCE_METADATA", "public_image": None})
        fuzzy = _fuzzy(features)
        source_ids = [x["source_id"] for x in hits if x["source_id"] is not None]
        warning = "SOURCE_CONCENTRATION_WARNING" if source_ids and len(set(source_ids)) == 1 else None
        segments.append({
            "segment_id": f"SEG_{window_id:04d}", "start_frame": int(window["start_frame"]), "end_frame": int(window["end_frame"]),
            "start_time_sec": start_sec, "end_time_sec": end_sec, "time_authority": "APPROXIMATE_FROM_DECODED_FRAME_INDEX_AND_REPORTED_FPS",
            "subject_identity_authority": "UNVERIFIED", "valid_pose_frames": int(window["detected_frames"]),
            "clip_encoded_frames": 1 if record else 0, "clip_sampling_status": "SAMPLED" if record else "NOT_SAMPLED", "evidence_quality": "OBSERVED_FRAME_FEATURES_IDENTITY_UNVERIFIED",
            "pose_observation": features, "clip_reference_hits": hits,
            "similarity_summary": {"mean_top3_cosine": float(np.mean([x["similarity"] for x in hits])) if hits else None, "semantics": "REFERENCE_SIMILARITY_NOT_BEHAVIOR_PROBABILITY"},
            "fuzzy_observation": fuzzy, "source_warning": warning,
            "review_assistance": f"{fuzzy['explanation_text']} CLIP Top-3는 유사도 기반 전문가 검토 보조 추천이며 참고 라벨은 확정 행동이 아닙니다.",
            "assistance_status": "MEASUREMENT_AND_SIMILARITY_BASED_EXPERT_REVIEW_ASSISTANCE",
            "behavior_status": "UNKNOWN", "l4": "DISABLED",
            "model_versions": payload["model_sha"], "missing_evidence": ["TRACK_ID_AUTHORITY", "EXPERT_BEHAVIOR_GROUND_TRUTH"] + ([] if hits else ["SEGMENT_CLIP_SAMPLE"]),
        })
    return segments
