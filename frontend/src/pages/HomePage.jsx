const MODULES = [
  {
    id: "my-persona",
    title: "My Persona",
    description: "Access your persistent 3D identity, inspect quality, and review your latest model state."
  },
  {
    id: "community",
    title: "Community",
    description: "Discover public personas, featured transformations, and proven improvement strategies."
  },
  {
    id: "connections",
    title: "Connections",
    description: "Build trusted networks and control who can view or collaborate on persona data."
  },
  {
    id: "build-persona",
    title: "Build My Persona",
    description: "Submit media to generate your baseline model, then run continuous improvements over time."
  }
];

export default function HomePage({ onNavigate }) {
  return (
    <section className="hero">
      <p className="eyebrow">Identity Reconstruction</p>
      <h1>Build and Evolve Your Olympus Persona</h1>
      <p>
        Olympus now organizes the platform around persona modules. Start with your own identity, connect
        with others, and continuously improve one persistent 3D model over time.
      </p>
      <button className="primary" onClick={() => onNavigate("build-persona")}>
        Build My Persona
      </button>
      <div className="module-grid">
        {MODULES.map((module) => (
          <article className="module-card" key={module.id}>
            <h3>{module.title}</h3>
            <p>{module.description}</p>
            <button className="ghost" onClick={() => onNavigate(module.id)}>
              Open
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
