import { useEffect, useState } from "react";
import { getJobAssets, getJobStatus, startJobPipeline } from "../services/api";

export default function ViewerPage({ activeJob }) {
  const [job, setJob] = useState(activeJob);
  const [assets, setAssets] = useState([]);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    setJob(activeJob);
  }, [activeJob]);

  useEffect(() => {
    if (!job?.id || job.status !== "processing") {
      return;
    }

    const timer = window.setInterval(() => {
      refreshStatus();
    }, 1500);

    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  async function refreshStatus() {
    if (!job?.id) {
      return;
    }

    try {
      const [latest, uploadedAssets] = await Promise.all([getJobStatus(job.id), getJobAssets(job.id)]);
      setJob(latest);
      setAssets(uploadedAssets);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "Unable to fetch job status.");
    }
  }

  async function handleStartPipeline() {
    if (!job?.id) {
      return;
    }

    setStarting(true);
    try {
      const next = await startJobPipeline(job.id);
      setJob(next);
      setError("");
      await refreshStatus();
    } catch (requestError) {
      setError(requestError.message || "Unable to start pipeline.");
    } finally {
      setStarting(false);
    }
  }

  return (
    <section className="panel">
      <h2>3D Output Viewer</h2>
      <p>
        This page will host the interactive Three.js viewer once generation assets are produced by the AI worker
        pipeline.
      </p>

      {!job ? (
        <p className="muted">No active job yet. Create a job in Upload first.</p>
      ) : (
        <div className="status-box">
          <p>
            <strong>Job ID:</strong> {job.id}
          </p>
          <p>
            <strong>Status:</strong> {job.status}
          </p>
          <p>
            <strong>Stage:</strong> {job.stage}
          </p>
          <button className="primary" onClick={refreshStatus}>
            Refresh Status
          </button>

          <button
            className="primary"
            onClick={handleStartPipeline}
            disabled={starting || job.status === "processing" || job.status === "completed"}
          >
            {starting ? "Starting..." : "Start Generation"}
          </button>

          <p>
            <strong>Uploaded assets:</strong> {assets.length}
          </p>

          {assets.length ? (
            <ul className="asset-list">
              {assets.map((asset) => (
                <li key={asset.file_key}>
                  <span>{asset.file_key}</span>
                  <span>{asset.status}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      )}

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
