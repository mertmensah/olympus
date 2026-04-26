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
    version = "1.0.0"

    def run(self, model_input: ReconstructAdapterInput) -> ReconstructAdapterOutput:
        """Generate a procedural 3D head mesh scaled by quality score."""
        face_signals = model_input.profile.get("face_signals", {}) if isinstance(model_input.profile, dict) else {}
        
        # Generate mesh based on quality score
        mesh = self._generate_head_mesh(
            quality_score=model_input.quality_score,
            height_cm=model_input.profile.get("height_cm", 175),
            face_signals=face_signals,
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
            },
        )

    def _generate_head_mesh(self, quality_score: float, height_cm: float, face_signals: dict) -> trimesh.Trimesh:
        """Generate a procedural head/bust mesh."""
        # Scale based on quality score (0.5 to 1.5x)
        q = max(0.0, min(1.0, float(quality_score)))
        scale = 0.7 + (q * 0.8)

        symmetry = float(face_signals.get("symmetry_score", 0.75))
        eye_contrast = float(face_signals.get("eye_contrast", 0.12))
        nose_bridge = float(face_signals.get("nose_bridge_contrast", 0.1))
        jaw_density = float(face_signals.get("jaw_edge_density", 0.15))

        head_width = 0.88 + (1.0 - jaw_density) * 0.22
        head_depth = 0.85 + nose_bridge * 0.8
        head_height = 1.05 + eye_contrast * 0.65
        
        # Create sphere base (head shape)
        sphere = trimesh.creation.icosphere(subdivisions=4)
        sphere.apply_scale([scale * head_width, scale * head_height, scale * head_depth])

        # Apply basic facial-region deformation to enforce face-like geometry.
        verts = sphere.vertices.copy()
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
        jaw_mask = y < (-scale * 0.16)
        jaw_factor = 1.0 - (jaw_density * 0.22)
        verts[jaw_mask, 0] *= jaw_factor

        # Symmetry regularization to avoid lopsided artifacts
        verts[:, 0] *= 0.85 + min(0.15, symmetry * 0.2)
        sphere.vertices = verts
        
        # Create cylinder (neck)
        neck = trimesh.creation.cylinder(
            radius=scale * 0.4,
            height=scale * 0.8,
        )
        neck.apply_translation([0, 0, -scale * 0.9])
        
        # Create box (shoulders/bust)
        bust = trimesh.creation.box(
            extents=[scale * 1.9, scale * 1.4, scale * 0.55]
        )
        bust.apply_translation([0, 0, -scale * 1.6])
        
        # Combine meshes
        combined = trimesh.util.concatenate([sphere, neck, bust])
        
        # Scale by height (normalize to ~175cm)
        height_scale = height_cm / 175.0
        combined.apply_scale(height_scale)
        
        return combined

    def _mesh_to_glb(self, mesh: trimesh.Trimesh) -> bytes:
        """Convert trimesh to GLB binary format."""
        glb_buffer = io.BytesIO()
        mesh.export(file_obj=glb_buffer, file_type="glb")
        return glb_buffer.getvalue()
