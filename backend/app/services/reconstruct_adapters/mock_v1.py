from __future__ import annotations

import io
from datetime import datetime, timezone

import numpy as np
import trimesh

from app.services.reconstruct_adapters.base import (
    ReconstructAdapter,
    ReconstructAdapterInput,
    ReconstructAdapterOutput,
)


class MockReconstructAdapterV1(ReconstructAdapter):
    name = "mock_v1"
    version = "1.2.0"

    def run(self, model_input: ReconstructAdapterInput) -> ReconstructAdapterOutput:
        """Generate a procedural 3D head mesh scaled by quality score."""
        face_signals = model_input.profile.get("face_signals", {}) if isinstance(model_input.profile, dict) else {}
        per_input_signals = (
            model_input.profile.get("per_input_face_signals", [])
            if isinstance(model_input.profile, dict)
            else []
        )
        
        # Start from a stable human-head prior and iteratively refine per input.
        mesh = self._generate_head_mesh(
            quality_score=model_input.quality_score,
            height_cm=model_input.profile.get("height_cm", 175),
            face_signals=face_signals,
            per_input_signals=per_input_signals,
        )
        
        # Export to GLB
        output_asset_key = f"{model_input.job_id}/outputs/reconstruction.glb"
        glb_bytes = self._mesh_to_glb(mesh)

        return ReconstructAdapterOutput(
            output_asset_key=output_asset_key,
            content_type="model/gltf-binary",
            payload_bytes=glb_bytes,
            adapter_name=self.name,
            adapter_version=self.version,
            metadata={
                "vertex_count": len(mesh.vertices),
                "face_count": len(mesh.faces),
                "selected_asset_count": len(model_input.selected_assets),
                "quality_score": model_input.quality_score,
                "face_signals_used": bool(face_signals),
                "generator_profile": "human_head_v2",
                "iteration_mode": "per_input_refinement",
                "iterations_applied": len(per_input_signals),
            },
        )

    def _generate_head_mesh(
        self,
        quality_score: float,
        height_cm: float,
        face_signals: dict,
        per_input_signals: list[dict],
    ) -> trimesh.Trimesh:
        """Generate a stable human head/bust mesh guided by facial signals."""
        q = max(0.0, min(1.0, float(quality_score)))
        scale = 0.85 + (q * 0.45)

        symmetry = float(np.clip(face_signals.get("symmetry_score", 0.75), 0.55, 0.98))
        eye_contrast = float(np.clip(face_signals.get("eye_contrast", 0.12), 0.03, 0.28))
        nose_bridge = float(np.clip(face_signals.get("nose_bridge_contrast", 0.1), 0.03, 0.22))
        jaw_density = float(np.clip(face_signals.get("jaw_edge_density", 0.15), 0.04, 0.35))

        head_width = 0.86 + (1.0 - jaw_density) * 0.16
        head_depth = 0.92 + nose_bridge * 0.35
        head_height = 1.08 + eye_contrast * 0.42

        # Cranial mass
        cranium = trimesh.creation.icosphere(subdivisions=4)
        cranium.apply_scale([scale * head_width, scale * head_height, scale * head_depth])
        cranium.apply_translation([0.0, scale * 0.10, 0.0])

        # Jaw/chin mass to ensure clear face silhouette (avoids knob-like body)
        jaw = trimesh.creation.icosphere(subdivisions=3)
        jaw.apply_scale([scale * 0.56, scale * 0.40, scale * 0.52])
        jaw.apply_translation([0.0, -scale * 0.56, scale * 0.12])

        # Nose as explicit protrusion
        nose = trimesh.creation.cone(radius=scale * 0.11, height=scale * (0.22 + nose_bridge * 0.35), sections=24)
        nose.apply_translation([0.0, scale * 0.05, scale * (0.86 + nose_bridge * 0.20)])

        # Ear anchors to reinforce human shape
        left_ear = trimesh.creation.icosphere(subdivisions=2)
        left_ear.apply_scale([scale * 0.11, scale * 0.17, scale * 0.08])
        left_ear.apply_translation([-scale * (0.88 + (1.0 - symmetry) * 0.04), scale * 0.05, 0.0])

        right_ear = left_ear.copy()
        right_ear.apply_translation([2 * scale * (0.88 + (1.0 - symmetry) * 0.04), 0.0, 0.0])

        # Apply basic facial-region deformation to enforce face-like geometry.
        verts = cranium.vertices.copy()
        x = verts[:, 0]
        y = verts[:, 1]
        z = verts[:, 2]

        # Nose ridge (front-center protrusion)
        nose_mask = (np.abs(x) < scale * 0.16) & (y > scale * 0.02) & (y < scale * 0.55) & (z > 0)
        verts[nose_mask, 2] += scale * (0.08 + (nose_bridge * 0.18))

        # Eye socket indentation band
        eye_mask = (np.abs(y - (scale * 0.22)) < scale * 0.12) & (np.abs(x) > scale * 0.12) & (z > 0)
        verts[eye_mask, 2] -= scale * (0.03 + eye_contrast * 0.07)

        # Jawline shaping in lower region
        jaw_mask = y < (-scale * 0.12)
        jaw_factor = 1.0 - (jaw_density * 0.18)
        verts[jaw_mask, 0] *= jaw_factor

        # Symmetry regularization to avoid lopsided artifacts
        verts[:, 0] *= 0.92 + min(0.08, symmetry * 0.10)
        cranium.vertices = verts
        
        # Create cylinder (neck)
        neck = trimesh.creation.cylinder(
            radius=scale * 0.30,
            height=scale * 0.72,
        )
        neck.apply_translation([0.0, -scale * 1.08, -scale * 0.02])
        
        # Create box (shoulders/bust)
        bust = trimesh.creation.box(
            extents=[scale * 1.85, scale * 1.05, scale * 0.58]
        )
        bust.apply_translation([0.0, -scale * 1.66, -scale * 0.06])
        
        # Combine meshes
        combined = trimesh.util.concatenate([cranium, jaw, nose, left_ear, right_ear, neck, bust])

        # Iteratively refine the same mesh after each input signal set.
        combined = self._apply_iterative_refinement(combined, scale, per_input_signals)
        
        # Scale by height (normalize to ~175cm)
        height_scale = height_cm / 175.0
        combined.apply_scale(height_scale)
        
        return combined

    def _apply_iterative_refinement(self, mesh: trimesh.Trimesh, scale: float, per_input_signals: list[dict]) -> trimesh.Trimesh:
        if not per_input_signals:
            return mesh

        verts = mesh.vertices.copy()
        total_steps = max(1, len(per_input_signals))

        for idx, signal_item in enumerate(per_input_signals):
            signals = signal_item.get("signals", {}) if isinstance(signal_item, dict) else {}
            symmetry = float(np.clip(signals.get("symmetry_score", 0.75), 0.55, 0.98))
            eye_contrast = float(np.clip(signals.get("eye_contrast", 0.12), 0.03, 0.28))
            nose_bridge = float(np.clip(signals.get("nose_bridge_contrast", 0.1), 0.03, 0.22))
            jaw_density = float(np.clip(signals.get("jaw_edge_density", 0.15), 0.04, 0.35))

            # Later inputs get slightly stronger influence to support iterative improvement.
            blend = 0.08 + (0.12 * ((idx + 1) / total_steps))

            x = verts[:, 0]
            y = verts[:, 1]
            z = verts[:, 2]

            # Mid-face refinement around eye/nose region.
            mid_mask = (y > -scale * 0.05) & (y < scale * 0.45) & (z > 0)
            verts[mid_mask, 2] += blend * scale * (0.02 + nose_bridge * 0.06)

            # Eye band indentation to separate brow/eye planes.
            eye_mask = (np.abs(y - (scale * 0.22)) < scale * 0.13) & (np.abs(x) > scale * 0.10) & (z > 0)
            verts[eye_mask, 2] -= blend * scale * (0.015 + eye_contrast * 0.04)

            # Jaw width adaptation in lower band.
            lower_mask = y < (-scale * 0.10)
            jaw_scale = 1.0 - (blend * (0.05 + jaw_density * 0.10))
            verts[lower_mask, 0] *= jaw_scale

            # Symmetry regularization to avoid random asymmetry artifacts.
            verts[:, 0] *= 0.98 + (symmetry - 0.55) * 0.03

        mesh.vertices = verts
        return mesh

    def _mesh_to_glb(self, mesh: trimesh.Trimesh) -> bytes:
        """Convert trimesh to GLB binary format."""
        glb_buffer = io.BytesIO()
        mesh.export(file_obj=glb_buffer, file_type="glb")
        return glb_buffer.getvalue()
