# Olympus Model Strategy

## MVP Reconstruction Path

1. Fast preview path:
   - Single-image 3D model for quick baseline output
2. High-fidelity path:
   - Multi-view reconstruction using extracted video frames and photos

## Candidate Open Model Families

- Image-to-3D models (for fast previews)
- Multi-view reconstruction stacks
- Gaussian splatting or neural rendering pipelines
- Segmentation and landmarking models

## Integration Pattern

- Worker receives `job_id` and media asset references.
- Pipeline writes intermediate artifacts by stage.
- API returns stage-level progress to the frontend.
- Final outputs standardized for web viewer consumption.

## License and Safety Gate

Before production use of any model:

- Confirm license allows intended deployment.
- Track model version and source URL.
- Record performance and quality benchmark notes.
