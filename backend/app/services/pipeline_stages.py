from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import tempfile
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from statistics import mean
from uuid import UUID

import imageio_ffmpeg
from PIL import Image, ImageFilter, ImageStat

from app.core.config import settings
from app.services.face_features import extract_face_signals
from app.services.database import DATA_DIR, database
from app.services.model_selector import get_model_selector
from app.services.reconstruct_adapters.base import ReconstructAdapterInput
from app.services.reconstruct_adapters.registry import get_reconstruct_adapter
from app.services.storage_service import storage_service

STAGE_OUTPUT_ROOT = DATA_DIR / "stage_outputs"
logger = logging.getLogger(__name__)


def _write_stage_output(job_id: UUID, stage: str, payload: dict) -> None:
    output_dir = STAGE_OUTPUT_ROOT / str(job_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{stage}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_ingest_stage(job_id: UUID) -> dict:
    assets = database.list_assets(job_id)
    uploaded = [asset for asset in assets if asset.status == "uploaded"]
    if not uploaded:
        raise RuntimeError("No uploaded assets found for ingest stage")

    payload = {
        "job_id": str(job_id),
        "ingested_count": len(uploaded),
        "asset_keys": [asset.file_key for asset in uploaded],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "ingest", payload)
    return payload


def run_quality_stage(job_id: UUID) -> dict:
    assets = [asset for asset in database.list_assets(job_id) if asset.status == "uploaded"]
    if not assets:
        raise RuntimeError("No uploaded assets available for quality stage")

    sizes = [asset.size_bytes for asset in assets]
    asset_reports: list[dict] = []

    for asset in assets:
        report = {
            "file_key": asset.file_key,
            "content_type": asset.content_type,
            "size_bytes": asset.size_bytes,
        }
        blob = storage_service.download_bytes(asset.file_key)

        if asset.content_type.startswith("image/"):
            report.update(_analyze_image(blob))
        elif asset.content_type.startswith("video/"):
            report.update(_analyze_video(blob))
        else:
            report["quality_score"] = 0.0
            report["note"] = "Unsupported media type for quality analysis"

        asset_reports.append(report)

    photos = sum(1 for asset in assets if asset.content_type.startswith("image/"))
    videos = sum(1 for asset in assets if asset.content_type.startswith("video/"))
    coverage_score = min(100.0, (photos * 6.0) + (videos * 16.0))
    asset_scores = [float(report.get("quality_score", 0.0)) for report in asset_reports]
    technical_score = mean(asset_scores) if asset_scores else 0.0
    input_feedback = [_build_input_feedback(report) for report in asset_reports]
    rejected_inputs = [item for item in input_feedback if item["value_level"] in {"rejected", "not_valuable"}]
    low_value_inputs = [item for item in input_feedback if item["value_level"] == "low"]

    payload = {
        "job_id": str(job_id),
        "quality_score": round((coverage_score + technical_score) / 2.0, 2),
        "coverage_score": round(coverage_score, 2),
        "technical_score": round(technical_score, 2),
        "assets_evaluated": len(assets),
        "size_stats": {
            "min_bytes": min(sizes),
            "max_bytes": max(sizes),
            "avg_bytes": round(mean(sizes), 2),
        },
        "asset_reports": asset_reports,
        "input_feedback": {
            "summary": {
                "inputs_total": len(input_feedback),
                "inputs_rejected_or_not_valuable": len(rejected_inputs),
                "inputs_low_value": len(low_value_inputs),
                "overall_readiness": _feedback_readiness(len(rejected_inputs), len(low_value_inputs), len(input_feedback)),
            },
            "per_input": input_feedback,
            "global_recommendations": _build_global_recommendations(input_feedback),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "quality", payload)
    return payload


def _feedback_readiness(rejected_count: int, low_count: int, total_count: int) -> str:
    if total_count == 0:
        return "insufficient"
    rejected_ratio = rejected_count / total_count
    low_ratio = low_count / total_count
    if rejected_ratio >= 0.4:
        return "poor"
    if rejected_ratio >= 0.2 or low_ratio >= 0.5:
        return "fair"
    return "good"


def _build_input_feedback(report: dict) -> dict:
    content_type = str(report.get("content_type", ""))
    quality = float(report.get("quality_score", 0.0))
    file_key = str(report.get("file_key", ""))
    media_type = str(report.get("media_type", "unknown"))

    inferred: list[str] = []
    could_not_infer: list[str] = []
    recommendations: list[str] = []
    rejection_reason: str | None = None

    if content_type.startswith("audio/"):
        value_level = "not_valuable"
        rejection_reason = "Audio is not currently used by reconstruction pipeline."
        could_not_infer.extend([
            "facial geometry",
            "head shape",
            "identity-aligned facial contours",
        ])
        recommendations.append("Keep audio for future persona traits, but upload clear portrait photos for facial likeness.")
    elif not content_type.startswith("image/") and not content_type.startswith("video/"):
        value_level = "rejected"
        rejection_reason = "Unsupported media type for current quality/reconstruction stages."
        could_not_infer.extend([
            "facial geometry",
            "head orientation",
        ])
        recommendations.append("Use JPG/PNG portraits or short MP4 clips with frontal and side angles.")
    else:
        brightness = float(report.get("brightness_mean", 0.0))
        edge_variance = float(report.get("edge_variance", 0.0))
        frame_count = int(report.get("frame_count", 0))

        if media_type == "image":
            inferred.append("basic facial contour sharpness")
            inferred.append("lighting/exposure quality")
            if 85 <= brightness <= 180:
                inferred.append("usable skin/face tonal separation")
            else:
                could_not_infer.append("stable facial tone boundaries")
                recommendations.append("Avoid overexposed/backlit selfies; use soft front lighting.")

            if edge_variance < 2.5:
                could_not_infer.append("high-confidence eye/nose/jaw contours")
                recommendations.append("Submit sharper photos (steady camera, no motion blur).")
        elif media_type == "video":
            inferred.append("temporal head-angle variety")
            if frame_count >= 3:
                inferred.append("multi-frame pose consistency")
            else:
                could_not_infer.append("reliable multi-angle face cues")
                recommendations.append("Use 3-8 second clips with slow head turn.")

        if quality >= 65:
            value_level = "high"
        elif quality >= 40:
            value_level = "medium"
        elif quality >= 20:
            value_level = "low"
            recommendations.append("Increase face fill ratio: face should occupy ~55-75% of frame.")
        else:
            value_level = "not_valuable"
            rejection_reason = "Input quality too low to reliably improve facial likeness."
            could_not_infer.append("identity-level facial detail")
            recommendations.append("Retake with higher resolution and neutral expression from eye level.")

    return {
        "file_key": file_key,
        "media_type": media_type,
        "content_type": content_type,
        "quality_score": round(quality, 2),
        "value_level": value_level,
        "inferred": sorted(set(inferred)),
        "could_not_infer": sorted(set(could_not_infer)),
        "recommendations": sorted(set(recommendations)),
        "rejection_reason": rejection_reason,
    }


def _build_global_recommendations(feedback_items: list[dict]) -> list[str]:
    recommendations: list[str] = []
    low_or_rejected = [item for item in feedback_items if item["value_level"] in {"low", "not_valuable", "rejected"}]
    videos = [item for item in feedback_items if item["media_type"] == "video"]
    images = [item for item in feedback_items if item["media_type"] == "image"]

    if low_or_rejected:
        recommendations.append("Replace low-value inputs with 6-12 sharp portrait photos under even frontal lighting.")
    if len(images) < 4:
        recommendations.append("Add more portrait photos: frontal, 30°, 60°, and profile angles.")
    if not videos:
        recommendations.append("Add one short slow-turn video to improve side-geometry consistency.")

    if not recommendations:
        recommendations.append("Current inputs are high-value; continue adding varied lighting and angle coverage for refinement.")

    return recommendations


def run_reconstruct_stage(job_id: UUID) -> dict:
    record = database.get_job_record(job_id)
    if not record:
        raise RuntimeError("Job record not found during reconstruct stage")

    artifacts = database.list_job_artifacts(job_id)
    quality_artifact = next((artifact for artifact in artifacts if artifact.stage == "quality"), None)
    quality_score_raw = float(quality_artifact.payload.get("quality_score", 0.0)) if quality_artifact else 0.0
    quality_score = max(0.0, min(1.0, quality_score_raw / 100.0))

    selected_assets = _select_reconstruction_assets(quality_artifact.payload if quality_artifact else {})
    face_signals = extract_face_signals(selected_assets)

    # Use intelligent model selection
    selector = get_model_selector()
    adapter, adapter_name = selector.select_adapter(
        quality_score=quality_score,
        asset_count=len(selected_assets)
    )
    selection_metadata = selector.get_selection_metadata(quality_score, len(selected_assets))
    selected_adapter = selection_metadata.get("selected_adapter", adapter_name)
    enforce_non_mock = os.getenv("OLYMPUS_ENFORCE_NON_MOCK_RECONSTRUCTION", "false").strip().lower() == "true"
    if selected_adapter == "mock_v1" and enforce_non_mock:
        raise RuntimeError(
            "Human-only mode blocks mock_v1 reconstruction. "
            "Configure a face-capable adapter or disable OLYMPUS_ENFORCE_NON_MOCK_RECONSTRUCTION for local demos."
        )

    logger.info(
        "Reconstruct selection",
        extra={
            "job_id": str(job_id),
            "adapter": adapter_name,
            "quality_score": round(quality_score, 4),
            "quality_score_raw": round(quality_score_raw, 2),
            "asset_count": len(selected_assets),
            "strategy": selection_metadata.get("strategy"),
            "face_signal_assets": int(face_signals.get("asset_count", 0)),
        },
    )

    adapter_input = ReconstructAdapterInput(
        job_id=str(job_id),
        selected_assets=selected_assets,
        quality_score=quality_score,
        profile={
            "age": record.age,
            "height_cm": record.height_cm,
            "subject_domain": "human",
            "reconstruction_focus": "facial_likeness",
            "face_signals": face_signals.get("signals", {}),
        },
    )

    tracemalloc.start()
    start_ts = perf_counter()
    try:
        adapter_output = adapter.run(adapter_input)
    finally:
        latency_ms = (perf_counter() - start_ts) * 1000.0
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    storage_service.upload_bytes(
        file_key=adapter_output.output_asset_key,
        content_type=adapter_output.content_type,
        payload=adapter_output.payload_bytes,
    )
    logger.info(
        "Reconstruct output uploaded",
        extra={
            "job_id": str(job_id),
            "file_key": adapter_output.output_asset_key,
            "content_type": adapter_output.content_type,
            "bytes": len(adapter_output.payload_bytes),
            "adapter": adapter_output.adapter_name,
        },
    )

    payload = {
        "job_id": str(job_id),
        "output_asset_key": adapter_output.output_asset_key,
        "estimated_vertices": int(adapter_output.metadata.get("estimated_vertices", 0)),
        "quality_score_input": round(quality_score, 4),
        "quality_score_input_raw": round(quality_score_raw, 2),
        "selected_assets": selected_assets,
        "face_signals": face_signals,
        "mode": "adapter-driven",
        "adapter": {
            "name": adapter_output.adapter_name,
            "version": adapter_output.adapter_version,
        },
        "runtime": {
            "latency_ms": round(latency_ms, 2),
            "peak_memory_kb": round(peak_bytes / 1024.0, 2),
            "output_size_bytes": len(adapter_output.payload_bytes),
            "content_type": adapter_output.content_type,
        },
        "model_selection": selection_metadata,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "reconstruct", payload)
    return payload


def run_postprocess_stage(job_id: UUID) -> dict:
    payload = {
        "job_id": str(job_id),
        "format": "glb",
        "lod_variants": ["high", "medium", "low"],
        "ready_for_delivery": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "postprocess", payload)
    return payload


def run_deliver_stage(job_id: UUID) -> dict:
    record = database.get_job_record(job_id)
    subject_glb_key: str | None = None
    subject_generation: int | None = None

    if record and record.subject_id:
        subject_id = record.subject_id
        artifacts = database.list_job_artifacts(job_id)
        reconstruct = next((a for a in artifacts if a.stage == "reconstruct"), None)
        quality = next((a for a in artifacts if a.stage == "quality"), None)

        if reconstruct:
            src_key: str = reconstruct.payload.get("output_asset_key", "")
            quality_score = float(quality.payload.get("quality_score", 0.0)) if quality else 0.0

            # Archive the previous current.glb as a revision (best-effort)
            existing = database.get_subject(subject_id)
            if existing and existing.current_glb_key:
                try:
                    archive_key = f"subjects/{subject_id}/revisions/{job_id}.glb"
                    storage_service.copy_bytes(existing.current_glb_key, archive_key)
                except Exception:
                    logger.warning("Could not archive previous GLB for subject %s", subject_id)

            # Promote new GLB to subjects/{id}/current.glb
            subject_glb_key = f"subjects/{subject_id}/current.glb"
            try:
                storage_service.copy_bytes(src_key, subject_glb_key)
                database.promote_subject_glb(subject_id, subject_glb_key, quality_score)
                database.add_subject_revision(subject_id, job_id, subject_glb_key, quality_score)
                subject_record = database.get_subject(subject_id)
                subject_generation = subject_record.generation if subject_record else None
                logger.info(
                    "Subject GLB promoted",
                    extra={"subject_id": str(subject_id), "job_id": str(job_id), "glb_key": subject_glb_key},
                )
            except Exception:
                logger.exception("Failed to promote GLB for subject %s", subject_id)

    # Clean up raw input assets after successful delivery (best-effort)
    _cleanup_input_assets(job_id)

    payload = {
        "job_id": str(job_id),
        "viewer_manifest": f"{job_id}/outputs/viewer-manifest.json",
        "delivery_status": "available",
        "subject_glb_key": subject_glb_key,
        "subject_generation": subject_generation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "deliver", payload)
    return payload


def _cleanup_input_assets(job_id: UUID) -> None:
    """Delete raw uploaded files from storage after pipeline completes. Non-fatal."""
    assets = [a for a in database.list_assets(job_id) if a.status == "uploaded"]
    for asset in assets:
        try:
            storage_service.delete_bytes(asset.file_key)
            logger.info("Deleted input asset %s", asset.file_key)
        except Exception:
            logger.warning("Could not delete input asset %s", asset.file_key)


_MAX_ANALYSIS_PX = 1024  # cap before PIL expands into RAM


def _analyze_image(blob: bytes) -> dict:
    with Image.open(io.BytesIO(blob)) as image:
        image.thumbnail((_MAX_ANALYSIS_PX, _MAX_ANALYSIS_PX), Image.LANCZOS)
        gray = image.convert("L")
        brightness = float(ImageStat.Stat(gray).mean[0])
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_variance = float(ImageStat.Stat(edges).var[0])
        del gray, edges  # release before next image

    exposure_score = max(0.0, 100.0 - abs(brightness - 128.0) * 0.9)
    sharpness_score = min(100.0, edge_variance * 4.0)
    quality_score = round((exposure_score + sharpness_score) / 2.0, 2)

    return {
        "media_type": "image",
        "brightness_mean": round(brightness, 2),
        "edge_variance": round(edge_variance, 4),
        "exposure_score": round(exposure_score, 2),
        "sharpness_score": round(sharpness_score, 2),
        "quality_score": quality_score,
    }


def _analyze_video(blob: bytes) -> dict:
    with tempfile.TemporaryDirectory(prefix="olympus-video-") as temp_dir:
        temp_path = Path(temp_dir)
        input_path = temp_path / "input.mp4"
        input_path.write_bytes(blob)
        frame_pattern = str(temp_path / "frame_%03d.jpg")

        try:
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(
                [ffmpeg_bin, "-y", "-i", str(input_path), "-vf", "fps=1", "-frames:v", "5", frame_pattern],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception as exc:
            return {
                "media_type": "video",
                "frame_count": 0,
                "quality_score": 0.0,
                "frame_extraction": "failed",
                "error": str(exc),
            }

        frames = sorted(temp_path.glob("frame_*.jpg"))
        if not frames:
            return {
                "media_type": "video",
                "frame_count": 0,
                "quality_score": 0.0,
                "frame_extraction": "no-frames",
            }

        frame_scores = []
        for frame_path in frames:
            frame_scores.append(_analyze_image(frame_path.read_bytes())["quality_score"])

        return {
            "media_type": "video",
            "frame_count": len(frames),
            "avg_frame_quality": round(mean(frame_scores), 2),
            "quality_score": round(mean(frame_scores), 2),
            "frame_extraction": "ffmpeg",
        }


def _select_reconstruction_assets(quality_payload: dict) -> list[str]:
    reports = quality_payload.get("asset_reports", [])
    scored = sorted(reports, key=lambda item: float(item.get("quality_score", 0.0)), reverse=True)
    photos = [item for item in scored if item.get("media_type") == "image"]
    if photos:
        return [item.get("file_key", "") for item in photos[:6] if item.get("file_key")]

    # Fallback for legacy payloads where media_type is missing.
    return [item.get("file_key", "") for item in scored[:6] if item.get("file_key")]
