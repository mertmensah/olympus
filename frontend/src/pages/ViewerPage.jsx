import { useEffect, useState } from "react";
import { getJobAssets, getJobStatus } from "../services/api";

export default function ViewerPage({ activeJob }) {
  const [job, setJob] = useState(activeJob);
  const [assets, setAssets] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    setJob(activeJob);
  }, [activeJob]);

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
