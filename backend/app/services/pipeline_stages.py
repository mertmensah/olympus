from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from uuid import UUID

from app.services.database import DATA_DIR, database

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
    photos = sum(1 for asset in assets if asset.content_type.startswith("image/"))
    videos = sum(1 for asset in assets if asset.content_type.startswith("video/"))

    coverage_score = min(100.0, (photos * 7.5) + (videos * 20.0))
    payload = {
        "job_id": str(job_id),
        "quality_score": round((coverage_score + min(100.0, mean(sizes) / 2048.0)) / 2.0, 2),
        "coverage_score": round(coverage_score, 2),
        "assets_evaluated": len(assets),
        "size_stats": {
            "min_bytes": min(sizes),
            "max_bytes": max(sizes),
            "avg_bytes": round(mean(sizes), 2),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_stage_output(job_id, "quality", payload)
    return payload


def run_reconstruct_stage(job_id: UUID) -> dict:
    record = database.get_job_record(job_id)
    if not record:
        raise RuntimeError("Job record not found during reconstruct stage")

    estimated_vertices = max(12000, record.media_summary.photo_count * 2500 + record.media_summary.video_count * 5000)
    payload = {
        "job_id": str(job_id),
        "output_asset_key": f"{job_id}/outputs/reconstruction.glb",
        "estimated_vertices": estimated_vertices,
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
