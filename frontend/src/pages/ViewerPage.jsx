import { useCallback, useEffect, useState } from "react";
import {
  getJobArtifacts,
  getJobAssets,
  getJobDebug,
  getJobInputFeedback,
  getJobStatus,
  getReconstructionFileUrl,
  startJobPipeline
} from "../services/api";
import ModelViewer from "../components/common/ModelViewer";

export default function ViewerPage({ activeJob }) {
  const [job, setJob] = useState(activeJob);
  const [assets, setAssets] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);
  const [modelLoaded, setModelLoaded] = useState(false);
  const [viewerStatus, setViewerStatus] = useState("Waiting for reconstruction output.");
  const [debugInfo, setDebugInfo] = useState(null);
  const [inputFeedback, setInputFeedback] = useState(null);

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
    if (level === "success") {
      setModelLoaded(true);
    }
    if (level === "error") {
      setModelLoaded(false);
    }
    setViewerStatus(`${level.toUpperCase()}: ${message}`);
  }, []);

  useEffect(() => {
    if (!job?.id || job.status !== "processing" || modelLoaded) {
      return;
    }

    const timer = window.setInterval(() => {
      refreshStatus();
    }, 1500);

    return () => window.clearInterval(timer);
  }, [job?.id, job?.status, modelLoaded]);

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
      const qualityArtifact = stageArtifacts.find(a => a.stage === "quality");
      if (reconstructArtifact && reconstructArtifact.payload) {
        const fileKey = reconstructArtifact.payload.output_asset_key;
        const contentType = reconstructArtifact.payload?.runtime?.content_type;
        if (fileKey) {
          if (contentType === "model/gltf-binary") {
            const nextModelUrl = getReconstructionFileUrl(job.id);
            setModelUrl((current) => (current === nextModelUrl ? current : nextModelUrl));
            if (!modelLoaded) {
              setViewerStatus(`Reconstruction artifact found: ${fileKey}`);
            }
          } else {
            setModelUrl(null);
            setModelLoaded(false);
            setViewerStatus(
              `Reconstruction output is ${contentType || "unknown"}, expected model/gltf-binary. Run a fresh job after backend restart.`
            );
          }
        } else {
          setModelLoaded(false);
          setViewerStatus("Reconstruct artifact exists, but output key is missing.");
        }
      } else {
        setModelLoaded(false);
        setViewerStatus("Reconstruct artifact not available yet.");
      }

      if (qualityArtifact) {
        try {
          const feedback = await getJobInputFeedback(job.id);
          setInputFeedback(feedback);
        } catch {
          setInputFeedback(null);
        }
      } else {
        setInputFeedback(null);
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

          {inputFeedback ? (
            <section className="input-feedback-section">
              <h3>Input Feedback</h3>
              <p>
                <strong>Readiness:</strong> {inputFeedback.summary?.overall_readiness || "n/a"}
              </p>
              <p>
                <strong>Rejected/Not Valuable:</strong>{" "}
                {inputFeedback.summary?.inputs_rejected_or_not_valuable ?? 0} / {inputFeedback.summary?.inputs_total ?? 0}
              </p>

              {Array.isArray(inputFeedback.global_recommendations) && inputFeedback.global_recommendations.length ? (
                <div className="feedback-global">
                  <strong>Global recommendations</strong>
                  <ul className="feedback-list">
                    {inputFeedback.global_recommendations.map((tip, idx) => (
                      <li key={`global-${idx}`}>{tip}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {Array.isArray(inputFeedback.per_input) && inputFeedback.per_input.length ? (
                <div className="feedback-grid">
                  {inputFeedback.per_input.map((item) => (
                    <article className="feedback-card" key={item.file_key}>
                      <p className="feedback-key"><strong>File:</strong> {item.file_key}</p>
                      <p>
                        <strong>Value:</strong> <span className={`value-badge value-${item.value_level}`}>{item.value_level}</span>
                      </p>
                      <p>
                        <strong>Used in reconstruction:</strong> {item.used_for_reconstruction ? "yes" : "no"}
                      </p>

                      {item.rejection_reason ? (
                        <p className="error"><strong>Reason:</strong> {item.rejection_reason}</p>
                      ) : null}

                      {Array.isArray(item.inferred) && item.inferred.length ? (
                        <div>
                          <strong>Model inferred</strong>
                          <ul className="feedback-list">
                            {item.inferred.map((value, idx) => (
                              <li key={`inferred-${item.file_key}-${idx}`}>{value}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {Array.isArray(item.could_not_infer) && item.could_not_infer.length ? (
                        <div>
                          <strong>Could not infer</strong>
                          <ul className="feedback-list">
                            {item.could_not_infer.map((value, idx) => (
                              <li key={`missing-${item.file_key}-${idx}`}>{value}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {Array.isArray(item.recommendations) && item.recommendations.length ? (
                        <div>
                          <strong>How to improve this input</strong>
                          <ul className="feedback-list">
                            {item.recommendations.map((value, idx) => (
                              <li key={`tip-${item.file_key}-${idx}`}>{value}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              ) : null}
            </section>
          ) : null}
        </div>
      )}

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
