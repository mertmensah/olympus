import { useState } from "react";
import { createJob } from "../services/api";

export default function UploadPage({ onJobCreated, onJumpToViewer }) {
  const [age, setAge] = useState(27);
  const [heightCm, setHeightCm] = useState(175);
  const [photoCount, setPhotoCount] = useState(20);
  const [videoCount, setVideoCount] = useState(2);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  async function handleCreateJob(event) {
    event.preventDefault();
    setStatus("loading");
    setError("");

    try {
      const payload = {
        age,
        height_cm: heightCm,
        media_summary: {
          photo_count: photoCount,
          video_count: videoCount
        }
      };

      const job = await createJob(payload);
      onJobCreated(job);
      setStatus("success");
      onJumpToViewer();
    } catch (requestError) {
      setError(requestError.message || "Failed to create generation job.");
      setStatus("error");
    }
  }

  return (
    <section className="panel">
      <h2>Create a Generation Job</h2>
      <p>This step captures the minimum metadata contract before media ingestion and processing.</p>
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

        <label>
          Planned photos
          <input
            type="number"
            min="10"
            max="60"
            value={photoCount}
            onChange={(e) => setPhotoCount(Number(e.target.value))}
          />
        </label>

        <label>
          Planned videos
          <input
            type="number"
            min="1"
            max="10"
            value={videoCount}
            onChange={(e) => setVideoCount(Number(e.target.value))}
          />
        </label>

        <button className="primary" type="submit" disabled={status === "loading"}>
          {status === "loading" ? "Creating..." : "Create Job"}
        </button>

        {error ? <p className="error">{error}</p> : null}
      </form>
    </section>
  );
}
