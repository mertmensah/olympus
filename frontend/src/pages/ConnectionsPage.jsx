export default function ConnectionsPage() {
  return (
    <section className="panel module-page">
      <p className="eyebrow">Connections</p>
      <h2>Manage Your Olympus Connections</h2>
      <p>
        Build a trusted network of people whose personas you can follow, collaborate with, or grant access to.
      </p>
      <div className="placeholder-grid">
        <article className="placeholder-card">
          <h3>Trusted Circle</h3>
          <p>Invite close contacts, share model revisions, and collaborate on appearance improvements.</p>
        </article>
        <article className="placeholder-card">
          <h3>Access Permissions</h3>
          <p>Define who can view, comment on, or remix your persona data and reconstruction outputs.</p>
        </article>
      </div>
    </section>
  );
}
