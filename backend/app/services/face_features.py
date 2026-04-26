from __future__ import annotations

import io
from statistics import mean

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageStat

from app.services.storage_service import storage_service


_MAX_FACE_IMAGES = 6
_FACE_CROP_RATIO = 0.72


def _center_face_crop(image: Image.Image) -> Image.Image:
    """Apply a human-portrait prior: centered upper-body/head framing."""
    rgb = image.convert("RGB")
    width, height = rgb.size

    side = int(min(width, height) * _FACE_CROP_RATIO)
    center_x = width // 2
    # Bias the crop upward where faces are typically located in portraits.
    center_y = int(height * 0.44)

    left = max(0, center_x - side // 2)
    top = max(0, center_y - side // 2)
    right = min(width, left + side)
    bottom = min(height, top + side)

    # Re-balance if crop clipped near edges.
    crop_w = right - left
    crop_h = bottom - top
    if crop_w != side:
        left = max(0, right - side)
    if crop_h != side:
        top = max(0, bottom - side)

    cropped = rgb.crop((left, top, min(width, left + side), min(height, top + side)))
    return cropped.resize((256, 256), Image.Resampling.LANCZOS)


def _single_image_face_signals(image_blob: bytes) -> dict[str, float]:
    with Image.open(io.BytesIO(image_blob)) as image:
        face = _center_face_crop(image)

    gray = ImageOps.grayscale(face)
    gray_np = np.asarray(gray, dtype=np.float32) / 255.0

    h, w = gray_np.shape
    upper = gray_np[: int(h * 0.45), :]
    middle = gray_np[int(h * 0.3) : int(h * 0.68), :]
    lower = gray_np[int(h * 0.62) :, :]

    left_half = gray_np[:, : w // 2]
    right_half = np.fliplr(gray_np[:, w - (w // 2) :])
    symmetry_score = float(1.0 - np.mean(np.abs(left_half - right_half)))

    eye_band = upper[int(upper.shape[0] * 0.3) : int(upper.shape[0] * 0.62), :]
    eye_contrast = float(np.std(eye_band))

    center_strip = middle[:, int(w * 0.42) : int(w * 0.58)]
    nose_bridge_contrast = float(np.std(center_strip))

    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges_np = np.asarray(edges, dtype=np.float32) / 255.0
    jaw_band = edges_np[int(h * 0.7) :, :]
    jaw_edge_density = float(np.mean(jaw_band > 0.22))

    rgb_mean = ImageStat.Stat(face).mean

    return {
        "symmetry_score": round(symmetry_score, 4),
        "eye_contrast": round(eye_contrast, 4),
        "nose_bridge_contrast": round(nose_bridge_contrast, 4),
        "jaw_edge_density": round(jaw_edge_density, 4),
        "avg_skin_r": round(float(rgb_mean[0]) / 255.0, 4),
        "avg_skin_g": round(float(rgb_mean[1]) / 255.0, 4),
        "avg_skin_b": round(float(rgb_mean[2]) / 255.0, 4),
    }


def extract_face_signals(asset_keys: list[str]) -> dict:
    """
    Extract compact face-centric signals from image assets.

    The signal set is not an identity embedding; it is a deterministic
    hint bundle that nudges reconstruction toward human facial structure.
    """
    image_keys = [key for key in asset_keys if "/photos/" in key][:_MAX_FACE_IMAGES]
    if not image_keys:
        return {"asset_count": 0, "signals": {}, "samples": [], "per_input": []}

    samples: list[dict[str, float]] = []
    per_input: list[dict] = []
    for key in image_keys:
        try:
            blob = storage_service.download_bytes(key)
            signal_set = _single_image_face_signals(blob)
            samples.append(signal_set)
            per_input.append(
                {
                    "file_key": key,
                    "signals": signal_set,
                }
            )
        except Exception:
            continue

    if not samples:
        return {"asset_count": 0, "signals": {}, "samples": [], "per_input": []}

    keys = samples[0].keys()
    aggregated = {k: round(mean(float(sample[k]) for sample in samples), 4) for k in keys}

    return {
        "asset_count": len(samples),
        "signals": aggregated,
        "samples": samples,
        "per_input": per_input,
    }
