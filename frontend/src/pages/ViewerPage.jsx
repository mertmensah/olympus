import { useCallback, useEffect, useState } from "react";
import { getJobArtifacts, getJobAssets, getJobDebug, getJobStatus, getReconstructionFileUrl, startJobPipeline } from "../services/api";
import ModelViewer from "../components/common/ModelViewer";

export default function ViewerPage({ activeJob }) {
  const [job, setJob] = useState(activeJob);
  const [assets, setAssets] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);
  const [viewerStatus, setViewerStatus] = useState("Waiting for reconstruction output.");
  const [debugInfo, setDebugInfo] = useState(null);

  useEffect(() => {
    if (!activeJob) {
      return;
    }
    setJob((current) => {
      if (!current || current.id !== activeJob.id) {
        return activeJob;
      }
      return current;
    });
  }, [activeJob]);

  const handleViewerStatusChange = useCallback(({ level, message }) => {
    setViewerStatus(`${level.toUpperCase()}: ${message}`);
  }, []);

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
        const contentType = reconstructArtifact.payload?.runtime?.content_type;
        if (fileKey) {
          if (contentType === "model/gltf-binary") {
            setModelUrl(getReconstructionFileUrl(job.id));
            setViewerStatus(`Reconstruction artifact found: ${fileKey}`);
          } else {
            setModelUrl(null);
            setViewerStatus(
              `Reconstruction output is ${contentType || "unknown"}, expected model/gltf-binary. Run a fresh job after backend restart.`
            );
          }
        } else {
          setViewerStatus("Reconstruct artifact exists, but output key is missing.");
        }
      } else {
        setViewerStatus("Reconstruct artifact not available yet.");
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

  async function handleRunDebugTrail() {
    if (!job?.id) {
      return;
    }
    try {
      const payload = await getJobDebug(job.id);
      setDebugInfo(payload);
      const storageOk = payload?.storage_probe?.ok;
      if (storageOk) {
        setViewerStatus("Debug trail: storage probe succeeded.");
      } else {
        setViewerStatus(`Debug trail: ${payload?.storage_probe?.error || "storage probe failed"}`);
      }
    } catch (requestError) {
      setError(requestError.message || "Unable to run debug trail.");
    }
  }

  return (
    <section className="panel">
      <h2>3D Output Viewer</h2>
      
      {modelUrl ? (
        <div style={{ marginBottom: "2rem" }}>
          <ModelViewer
            modelUrl={modelUrl}
            onStatusChange={handleViewerStatusChange}
          />
          <p style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "#999" }}>
            Use mouse to rotate, scroll to zoom, right-click to pan
          </p>
          <p style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "#ccc" }}>
            Viewer status: {viewerStatus}
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

          <button className="primary" onClick={handleRunDebugTrail}>
            Run Debug Trail
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

          {debugInfo ? (
            <pre style={{ whiteSpace: "pre-wrap", marginTop: "1rem", fontSize: "0.85rem" }}>
              {JSON.stringify(debugInfo, null, 2)}
            </pre>
          ) : null}
        </div>
      )}

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
