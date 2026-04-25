# Olympus Project Plan

## 1. Product Goal

Build a web platform where users can create a digital 3D likeness of themselves by uploading multimedia inputs:

- Photos
- Video clips
- Audio clips (for optional voice-linked profile)

The generated 3D result should be viewable in-app and tied to basic user metadata such as age and height.

## 2. Core User Experience

1. User signs up and creates a profile.
2. User uploads required media set.
3. User enters optional profile parameters (age, height, notes).
4. AI pipeline validates media quality and coverage.
5. System runs image/video-to-3D reconstruction pipeline.
6. User previews 3D likeness in browser.
7. User can regenerate with improved inputs.

## 3. MVP Scope

### In Scope

- Account system with secure media upload
- Guided capture checklist for users
- Media validation (blur, lighting, face coverage)
- 3D generation pipeline using publicly available models
- Browser 3D viewer for output mesh/gaussian/splat result
- Job queue and progress tracking
- Basic metadata storage (age, height)

### Out of Scope (MVP)

- Real-time animation from text chat
- Full-body motion cloning
- Marketplace/social features
- Enterprise APIs

## 4. Recommended Technical Architecture

### Frontend

- React + Vite
- Three.js or Babylon.js for 3D display
- Upload wizard with progress and quality hints

### Backend

- Python FastAPI service
- Worker queue (Celery or RQ)
- Object storage for media and outputs
- Postgres for metadata and job tracking

### AI Processing Layer

- Stage A: Frame extraction and quality scoring
- Stage B: Face/body reconstruction pipeline
- Stage C: Mesh/point-cloud post-processing
- Stage D: Standardized export for web viewer

## 5. Public Model Strategy (Initial)

Use free/publicly available models with permissive licenses where possible.

### Candidate Families to Evaluate

- Multi-view human/face reconstruction models
- Single-image to 3D avatar/mesh models
- Gaussian splatting or neural rendering models
- Face landmarking and segmentation models

### Selection Criteria

- License clarity for commercial/production use
- GPU requirements and inference time
- Reconstruction quality under non-ideal input
- Ease of integration and export format support

## 6. Data Contract

### User Inputs

- 10-30 photos across angles and lighting
- 1-3 short videos for extra coverage
- Optional voice clips
- Metadata: age, height, country/timezone (optional)

### Outputs

- Primary 3D asset (glb/usdz/ply depending on model)
- Render thumbnails and turntable preview
- Quality score and confidence indicators

## 7. Security and Privacy Requirements

- Explicit user consent at upload
- Encryption at rest for media storage
- Time-bound signed URLs for access
- Per-user isolation for outputs
- Deletion workflow for all uploaded and generated media
- Audit logs for processing steps

## 8. Milestones

### Milestone 0: Discovery and Feasibility (1-2 weeks)

- Evaluate 3-5 public reconstruction model stacks
- Benchmark cost, speed, and quality
- Choose baseline pipeline for MVP

### Milestone 1: Platform Foundation (2 weeks)

- Auth, storage, upload wizard, metadata capture
- Job queue setup and status API

### Milestone 2: First End-to-End Generation (2-3 weeks)

- Integrate baseline model pipeline
- Produce first in-app 3D outputs

### Milestone 3: Quality and Reliability (2 weeks)

- Add media quality gating
- Improve post-processing and retries
- Add operational monitoring

### Milestone 4: Closed Beta (2 weeks)

- Small test cohort
- Feedback loop and model/pipeline tuning

## 9. Team and Resource Needs

- 1 frontend engineer
- 1 backend/platform engineer
- 1 ML engineer
- 1 product/designer (part-time)
- GPU inference environment (self-hosted or managed)

## 10. Success Metrics

- Generation success rate
- Median processing time per user job
- User-rated likeness score
- Regeneration rate and retention

## 11. Immediate Next Actions

1. Lock final model shortlist and licensing review.
2. Define exact media capture requirements per user flow.
3. Build thin vertical slice: upload -> process -> 3D viewer.
4. Run internal quality tests with 20 sample profiles.
