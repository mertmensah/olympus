import { useEffect, useState } from "react";
import { getJobArtifacts, getJobAssets, getJobStatus, startJobPipeline } from "../services/api";
import ModelViewer from "../components/common/ModelViewer";
import { getSupabaseStorageUrl } from "../supabase";

export default function ViewerPage({ activeJob }) {
  const [job, setJob] = useState(activeJob);
  const [assets, setAssets] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);

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
      const [latest, uploadedAssets, stageArtifacts] = await Promise.all([
        getJobStatus(job.id),
        getJobAssets(job.id),
        getJobArtifacts(job.id)
      ]);
      setJob(latest);
      setAssets(uploadedAssets);
      setArtifacts(stageArtifacts);
      
      // Extract reconstruct artifact and get model URL
      const reconstructArtifact = stageArtifacts.find(a => a.stage === "reconstruct");
      if (reconstructArtifact && reconstructArtifact.payload) {
        const fileKey = reconstructArtifact.payload.output_asset_key;
        if (fileKey) {
          const supabaseUrl = getSupabaseStorageUrl(fileKey);
          setModelUrl(supabaseUrl);
        }
      }
      
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
      
      {modelUrl ? (
        <div style={{ marginBottom: "2rem" }}>
          <ModelViewer modelUrl={modelUrl} />
          <p style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "#999" }}>
            Use mouse to rotate, scroll to zoom, right-click to pan
          </p>
        </div>
      ) : (
        <p className="muted">
          {job?.status === "completed" && job?.stage === "deliver"
            ? "3D model generation complete. Model was reconstructed but is loading..."
            : "Upload assets and start generation to see the 3D model here."}
        </p>
      )}

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

          <p>
            <strong>Stage artifacts:</strong> {artifacts.length}
          </p>

          {artifacts.length ? (
            <ul className="artifact-list">
              {artifacts.map((artifact, idx) => (
                <li key={`${artifact.stage}-${idx}`}>
                  <span>{artifact.stage}</span>
                  <span>{artifact.created_at}</span>
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
