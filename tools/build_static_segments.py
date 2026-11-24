from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "app/static/demo/samples/demo-001/pose-frames.json"
OUTPUT = ROOT / "app/static/demo/samples/demo-001/segments.json"
CONFIDENCE = 0.12
WINDOW = 60


def ramp_down(value: float, full_until: float, zero_at: float) -> float:
    return 1.0 if value <= full_until else 0.0 if value >= zero_at else (zero_at - value) / (zero_at - full_until)


def triangle(value: float, left: float, peak: float, right: float) -> float:
    if value <= left or value >= right:
        return 0.0
    return (value - left) / (peak - left) if value < peak else (right - value) / (right - peak)


def ramp_up(value: float, zero_until: float, full_at: float) -> float:
    return 0.0 if value <= zero_until else 1.0 if value >= full_at else (value - zero_until) / (full_at - zero_until)


def features(frames: list[dict]) -> dict:
    ratios = [sum(p["confidence"] > CONFIDENCE for p in f["keypoints"]) / 17 for f in frames]
    changes: list[float] = []
    for previous, current in zip(frames, frames[1:]):
        pairs = [(a, b) for a, b in zip(previous["keypoints"], current["keypoints"]) if a["confidence"] > CONFIDENCE and b["confidence"] > CONFIDENCE]
        if not pairs:
            continue
        xs = [b["x"] for _, b in pairs]
        ys = [b["y"] for _, b in pairs]
        diagonal = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        if diagonal <= 1e-6:
            continue
        displacements = [math.hypot(b["x"] - a["x"], b["y"] - a["y"]) / diagonal for a, b in pairs]
        changes.append(statistics.median(displacements))
    representative = frames[len(frames) // 2]
    valid = [p for p in representative["keypoints"] if p["confidence"] > CONFIDENCE]
    thumbnail = None
    if valid:
        min_x, min_y = min(p["x"] for p in valid), min(p["y"] for p in valid)
        scale = max(max(p["x"] for p in valid) - min_x, max(p["y"] for p in valid) - min_y, 1e-6)
        thumbnail = [{"x": (p["x"] - min_x) / scale, "y": (p["y"] - min_y) / scale, "confidence": p["confidence"]} if p["confidence"] > CONFIDENCE else {"x": None, "y": None, "confidence": p["confidence"]} for p in representative["keypoints"]]
    return {
        "valid_joint_ratio": statistics.mean(ratios) if ratios else 0.0,
        "normalized_pose_change_median": statistics.median(changes) if changes else None,
        "normalized_pose_change_std": statistics.pstdev(changes) if len(changes) > 1 else 0.0 if changes else None,
        "valid_change_pairs": len(changes),
        "selection_policy": "FROZEN_SINGLE_SKELETON_PER_FRAME_NO_TRACK_AUTHORITY",
        "subject_identity_authority": "UNVERIFIED",
        "query_pose_thumbnail": {"schema": "AP10K_NATIVE17", "coordinates": thumbnail, "authority": "QUERY_OBSERVATION_VISUALIZATION", "normalization": "VALID_JOINT_BBOX_MAX_AXIS", "source_frame_index": representative["frame_index"]} if thumbnail else None,
    }


def fuzzy(observation: dict) -> dict:
    value = observation["normalized_pose_change_median"]
    coverage = observation["valid_joint_ratio"]
    memberships = {
        "motion_low": None if value is None else ramp_down(value, 0.01, 0.04),
        "motion_moderate": None if value is None else triangle(value, 0.01, 0.04, 0.08),
        "motion_high": None if value is None else ramp_up(value, 0.04, 0.08),
        "coverage_sufficient": ramp_up(coverage, 0.35, 0.75),
    }
    if value is None or coverage < 0.5:
        category = "OBSERVATION_INSUFFICIENT"
        explanation = "유효 관절 관측 또는 연속 변화 쌍이 부족합니다."
    else:
        scores = {"POSE_VARIATION_LOW": memberships["motion_low"], "POSE_VARIATION_MODERATE": memberships["motion_moderate"], "POSE_VARIATION_HIGH": memberships["motion_high"]}
        category = max(scores, key=scores.get)
        explanation = "실제 관절 좌표 변화량의 기술 설계 소속도에 따른 관측 변화 범주이며 전문가 검토 보조 계측입니다."
    return {
        "rule_id": "POSE_VARIATION_MEMBERSHIP_WITH_COVERAGE_AND_IDENTITY_GATE",
        "rule_version": "FRAME_OBSERVATION_FUZZY_V2_IDENTITY_GATED",
        "memberships": memberships,
        "membership_design_authority": "TECHNICAL_DESIGN_NOT_EXPERT_VALIDATED",
        "output_category": category,
        "explanation_text": explanation,
        "probability": None,
        "interpretation_scope": "FRAME_LEVEL_POSE_VARIATION_MEASUREMENT",
        "identity_caveat": "동일 개체 추적은 검증되지 않았습니다.",
    }


def main() -> None:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    frames = payload["frames"]
    segments = []
    for number, start in enumerate(range(0, len(frames), WINDOW)):
        chunk = frames[start : start + WINDOW]
        observation = features(chunk)
        segments.append({
            "segment_id": f"SEG_{number:04d}",
            "frame_start": chunk[0]["frame_index"],
            "frame_end": chunk[-1]["frame_index"],
            "start_time_sec": chunk[0].get("pts_sec"),
            "end_time_sec": chunk[-1].get("pts_sec"),
            "time_authority": "UI_APPROXIMATION_FROM_FROZEN_PTS_FIELD_NOT_EVENT_TIMESTAMP",
            "pose_observation": observation,
            "fuzzy_observation": fuzzy(observation),
            "clip_sampling_status": "NOT_SAMPLED",
            "clip_reference_hits": [],
            "source_warning": "NO_SEGMENT_CLIP_EMBEDDING",
            "evidence_quality": "FROZEN_POSE_OBSERVATION_IDENTITY_UNVERIFIED",
            "behavior_status": "UNKNOWN",
        })
    OUTPUT.write_text(json.dumps({"schema": "mambatail.segment-observation.v1", "frame_count": len(frames), "segment_count": len(segments), "segments": segments}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
