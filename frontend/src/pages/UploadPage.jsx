import { useState } from "react";
import { createJob, createUploadSession, uploadToTarget } from "../services/api";

function buildDescriptors(files, kind) {
  return files.map((file, index) => ({
    client_id: `${kind}-${index}`,
    kind,
    file_name: file.name,
    content_type: file.type || "application/octet-stream",
    size_bytes: file.size
  }));
}

export default function UploadPage({ onJobCreated, onJumpToViewer }) {
  const [age, setAge] = useState(27);
  const [heightCm, setHeightCm] = useState(175);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [sessionSummary, setSessionSummary] = useState(null);
  const [photoFiles, setPhotoFiles] = useState([]);
  const [videoFiles, setVideoFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);

  function mapFiles(event, setter) {
    const files = Array.from(event.target.files || []);
    setter(files);
  }

  async function handleCreateJob(event) {
    event.preventDefault();
    setStatus("loading");
    setError("");

    try {
      if (photoFiles.length === 0) {
        throw new Error("Select at least one photo to proceed.");
      }

      const payload = {
        age,
        height_cm: heightCm,
        media_summary: {
          photo_count: photoFiles.length,
          video_count: videoFiles.length
        }
      };

      const job = await createJob(payload);

      const descriptors = [...buildDescriptors(photoFiles, "photo"), ...buildDescriptors(videoFiles, "video")];

      const uploadSession = await createUploadSession(job.id, descriptors);
      const fileByClientId = new Map(descriptors.map((descriptor, index) => [descriptor.client_id, [...photoFiles, ...videoFiles][index]]));

      let uploaded = 0;
      for (const target of uploadSession.targets) {
        const file = fileByClientId.get(target.client_id);
        if (!file) {
          continue;
        }
        await uploadToTarget(target, file);
        uploaded += 1;
        setUploadProgress(Math.round((uploaded / uploadSession.targets.length) * 100));
      }

      setSessionSummary({
        totalTargets: uploadSession.targets.length,
        expiresInSeconds: uploadSession.expires_in_seconds,
        previewTarget: uploadSession.targets[0] || null,
        uploadedCount: uploaded
      });

      onJobCreated({ ...job, uploadSession });
      setStatus("success");
    } catch (requestError) {
      setError(requestError.message || "Failed to create generation job.");
      setStatus("error");
    }
  }

  return (
    <section className="panel">
      <p className="eyebrow">Build My Persona</p>
      <h2>Persona Construction Flow</h2>
      <p>Submit baseline identity media first, then iterate with refinement uploads over time.</p>

      <div className="build-steps">
        <article className="step-card">
          <h3>Step 1: Identity Profile</h3>
          <p>Set core baseline metadata used during mesh scaling and profile context.</p>
        </article>
        <article className="step-card">
          <h3>Step 2: Capture Upload</h3>
          <p>Upload portraits and optional videos with clean lighting and angle variation.</p>
        </article>
        <article className="step-card">
          <h3>Step 3: Build + Inspect</h3>
          <p>Run generation, inspect feedback, then continue refinement cycles from My Persona.</p>
        </article>
      </div>

      <form onSubmit={handleCreateJob} className="form-grid">
        <label>
          Age
          <input type="number" min="13" max="110" value={age} onChange={(e) => setAge(Number(e.target.value))} />
        </label>

        <label>
          Height (cm)
          <input
            type="number"
            min="100"
            max="240"
            value={heightCm}
            onChange={(e) => setHeightCm(Number(e.target.value))}
          />
        </label>

        <label className="file-field">
          Photo files
          <input type="file" accept="image/*" multiple onChange={(e) => mapFiles(e, setPhotoFiles)} />
          <small>{photoFiles.length} selected</small>
        </label>

        <label className="file-field">
          Video files
          <input type="file" accept="video/*" multiple onChange={(e) => mapFiles(e, setVideoFiles)} />
          <small>{videoFiles.length} selected</small>
        </label>

        <button className="primary" type="submit" disabled={status === "loading"}>
          {status === "loading" ? "Creating..." : "Create Job"}
        </button>

        {status === "loading" ? <p className="muted">Upload progress: {uploadProgress}%</p> : null}

        {sessionSummary ? (
          <div className="status-box session-box">
            <p className="muted"><strong>Upload session ready</strong></p>
            <p>
              <strong>Upload targets generated:</strong> {sessionSummary.totalTargets}
            </p>
            <p>
              <strong>Files uploaded:</strong> {sessionSummary.uploadedCount}
            </p>
            <p>
              <strong>Session expiry:</strong> {sessionSummary.expiresInSeconds} seconds
            </p>
            <p>
              <strong>First target key:</strong> {sessionSummary.previewTarget?.file_key || "n/a"}
            </p>
            <button type="button" className="primary" onClick={onJumpToViewer}>
              Continue to Viewer
            </button>
          </div>
        ) : null}

        {error ? <p className="error">{error}</p> : null}
      </form>
    </section>
  );
}
