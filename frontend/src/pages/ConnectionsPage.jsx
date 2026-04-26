import { useEffect, useMemo, useState } from "react";
import { acceptConnection, declineConnection, listConnections, requestConnection } from "../services/api";

export default function ConnectionsPage() {
  const [connections, setConnections] = useState([]);
  const [targetUserId, setTargetUserId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refreshConnections() {
    setLoading(true);
    try {
      const result = await listConnections();
      setConnections(result);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "Unable to load connections.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshConnections();
  }, []);

  const incomingPending = useMemo(
    () => connections.filter((item) => item.status === "pending"),
    [connections]
  );

  const accepted = useMemo(
    () => connections.filter((item) => item.status === "accepted"),
    [connections]
  );

  async function handleRequestConnection(event) {
    event.preventDefault();
    if (!targetUserId.trim()) {
      return;
    }
    try {
      await requestConnection(targetUserId.trim());
      setTargetUserId("");
      await refreshConnections();
    } catch (requestError) {
      setError(requestError.message || "Could not send connection request.");
    }
  }

  async function handleDecision(connectionId, decision) {
    try {
      if (decision === "accept") {
        await acceptConnection(connectionId);
      } else {
        await declineConnection(connectionId);
      }
      await refreshConnections();
    } catch (requestError) {
      setError(requestError.message || "Unable to update connection request.");
    }
  }

  return (
    <section className="panel module-page">
      <p className="eyebrow">Connections</p>
      <h2>Manage Your Olympus Connections</h2>
      <p>
        Build a trusted network of people whose personas you can follow, collaborate with, or grant access to.
      </p>

      <form className="connection-form" onSubmit={handleRequestConnection}>
        <label>
          Connect with user id
          <input
            type="text"
            value={targetUserId}
            onChange={(event) => setTargetUserId(event.target.value)}
            placeholder="target user id"
          />
        </label>
        <button type="submit" className="primary">Send Request</button>
      </form>

      <div className="placeholder-grid">
        <article className="placeholder-card">
          <h3>Incoming Requests</h3>
          {loading ? <p>Loading...</p> : null}
          {!loading && incomingPending.length === 0 ? <p className="muted">No pending requests.</p> : null}
          {incomingPending.map((item) => (
            <div key={item.id} className="connection-row">
              <span>{item.requester_user_id}</span>
              <div className="connection-actions">
                <button className="ghost" type="button" onClick={() => handleDecision(item.id, "accept")}>Accept</button>
                <button className="ghost" type="button" onClick={() => handleDecision(item.id, "decline")}>Decline</button>
              </div>
            </div>
          ))}
        </article>

        <article className="placeholder-card">
          <h3>Trusted Circle</h3>
          {loading ? <p>Loading...</p> : null}
          {!loading && accepted.length === 0 ? <p className="muted">No accepted connections yet.</p> : null}
          {accepted.map((item) => (
            <div key={item.id} className="connection-row">
              <span>{item.requester_user_id} ↔ {item.target_user_id}</span>
              <span className="value-badge value-high">accepted</span>
            </div>
          ))}
        </article>
      </div>

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
