const TOKENS = [
  { name: "Sky 050", cssVar: "--ol-color-sky-050", sampleClass: "swatch-sky-050" },
  { name: "Sky 200", cssVar: "--ol-color-sky-200", sampleClass: "swatch-sky-200" },
  { name: "Sky 400", cssVar: "--ol-color-sky-400", sampleClass: "swatch-sky-400" },
  { name: "Sky 700", cssVar: "--ol-color-sky-700", sampleClass: "swatch-sky-700" },
  { name: "Panel", cssVar: "--ol-panel-solid", sampleClass: "swatch-panel" },
  { name: "Line", cssVar: "--ol-line", sampleClass: "swatch-line" }
];

export default function StyleGuidePage() {
  return (
    <section className="panel module-page">
      <p className="eyebrow">Style Guide</p>
      <h2>Olympus Design System</h2>
      <p>
        This page documents the visual foundations used across Olympus so the experience stays consistent as
        new modules are added.
      </p>

      <section className="style-guide-section">
        <h3>Color Tokens</h3>
        <div className="token-grid">
          {TOKENS.map((token) => (
            <article className="token-card" key={token.name}>
              <span className={`token-swatch ${token.sampleClass}`} aria-hidden="true" />
              <strong>{token.name}</strong>
              <p>{token.cssVar}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="style-guide-section">
        <h3>Core Actions</h3>
        <div className="style-row">
          <button className="primary" type="button">Primary Action</button>
          <button className="ghost" type="button">Secondary Action</button>
          <button className="ghost" type="button" disabled>Disabled</button>
        </div>
      </section>

      <section className="style-guide-section">
        <h3>Cards and Surfaces</h3>
        <div className="placeholder-grid">
          <article className="module-card">
            <h4>Module Card</h4>
            <p>Used for module entry points and concise summaries.</p>
          </article>
          <article className="status-box">
            <h4>Status Box</h4>
            <p>Used for operational state, diagnostics, and feedback sections.</p>
          </article>
        </div>
      </section>
    </section>
  );
}
