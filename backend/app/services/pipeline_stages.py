from __future__ import annotations

import io
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from uuid import UUID

import imageio_ffmpeg
from PIL import Image, ImageFilter, ImageStat

from app.services.database import DATA_DIR, database
from app.services.storage_service import storage_service

STAGE_OUTPUT_ROOT = DATA_DIR / "stage_outputs"


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

    estimated_vertices = max(12000, record.media_summary.photo_count * 2500 + record.media_summary.video_count * 5000)
    payload = {
        "job_id": str(job_id),
        "output_asset_key": f"{job_id}/outputs/reconstruction.glb",
        "estimated_vertices": int(estimated_vertices + (quality_score * 35)),
        "quality_score_input": round(quality_score, 2),
        "selected_assets": _select_reconstruction_assets(quality_artifact.payload if quality_artifact else {}),
        "mode": "placeholder-reconstruction",
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


def _analyze_image(blob: bytes) -> dict:
    with Image.open(io.BytesIO(blob)) as image:
        gray = image.convert("L")
        brightness = float(ImageStat.Stat(gray).mean[0])
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_variance = float(ImageStat.Stat(edges).var[0])

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
