import { useEffect, useMemo, useState } from "react";
import { listConnections } from "../services/api";

const COMMUNITY_FEED = [
  {
    title: "Featured Persona",
    detail: "A full multi-angle portrait set reached confidence tier 92 after three refinement rounds."
  },
  {
    title: "Capture Insight",
    detail: "Users with one smooth 5-second head-turn video improved side-profile consistency significantly."
  },
  {
    title: "Olympus Standard",
    detail: "Even frontal light and neutral expression still produce the most stable baseline mesh quality."
  }
];

export default function CommunityPage() {
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const result = await listConnections();
        if (active) {
          setConnections(result);
          setError("");
        }
      } catch (requestError) {
        if (active) {
          setError(requestError.message || "Could not load community context.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  const acceptedCount = useMemo(
    () => connections.filter((item) => item.status === "accepted").length,
    [connections]
  );

  return (
    <section className="panel module-page">
      <p className="eyebrow">Community</p>
      <h2>Olympus Commons</h2>
      <p>
        Track ecosystem best practices, community quality trends, and your network reach as Olympus expands.
      </p>

      <div className="community-metrics">
        <article className="metric-card">
          <strong>Connected Circle</strong>
          <p>{loading ? "..." : acceptedCount}</p>
        </article>
        <article className="metric-card">
          <strong>Pending Requests</strong>
          <p>{loading ? "..." : connections.filter((item) => item.status === "pending").length}</p>
        </article>
        <article className="metric-card">
          <strong>Community Feed</strong>
          <p>Live Insights</p>
        </article>
      </div>

      <div className="placeholder-grid">
        {COMMUNITY_FEED.map((item) => (
          <article className="placeholder-card" key={item.title}>
            <h3>{item.title}</h3>
            <p>{item.detail}</p>
          </article>
        ))}
      </div>

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
