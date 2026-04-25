from __future__ import annotations

import io
import json
import logging
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
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "quality", payload)
    return payload


def run_reconstruct_stage(job_id: UUID) -> dict:
    record = database.get_job_record(job_id)
    if not record:
        raise RuntimeError("Job record not found during reconstruct stage")

    artifacts = database.list_job_artifacts(job_id)
    quality_artifact = next((artifact for artifact in artifacts if artifact.stage == "quality"), None)
    quality_score = float(quality_artifact.payload.get("quality_score", 0.0)) if quality_artifact else 0.0

    selected_assets = _select_reconstruction_assets(quality_artifact.payload if quality_artifact else {})

    # Use intelligent model selection
    selector = get_model_selector()
    adapter, adapter_name = selector.select_adapter(
        quality_score=quality_score,
        asset_count=len(selected_assets)
    )
    selection_metadata = selector.get_selection_metadata(quality_score, len(selected_assets))
    logger.info(
        "Reconstruct selection",
        extra={
            "job_id": str(job_id),
            "adapter": adapter_name,
            "quality_score": round(quality_score, 2),
            "asset_count": len(selected_assets),
            "strategy": selection_metadata.get("strategy"),
        },
    )

    adapter_input = ReconstructAdapterInput(
        job_id=str(job_id),
        selected_assets=selected_assets,
        quality_score=quality_score,
        profile={"age": record.age, "height_cm": record.height_cm},
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
        "quality_score_input": round(quality_score, 2),
        "selected_assets": selected_assets,
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
    payload = {
        "job_id": str(job_id),
        "viewer_manifest": f"{job_id}/outputs/viewer-manifest.json",
        "delivery_status": "available",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "deliver", payload)
    return payload


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
    return [item.get("file_key", "") for item in scored[:6] if item.get("file_key")]
