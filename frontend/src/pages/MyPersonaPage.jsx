import ViewerPage from "./ViewerPage";

export default function MyPersonaPage({ activeJob, onBuildPersona }) {
  return (
    <section className="module-stack">
      <section className="panel module-page">
        <p className="eyebrow">My Persona</p>
        <h2>Your Persistent Digital Persona</h2>
        <p>
          This module is your primary identity space. Track reconstruction quality, inspect model output,
          and launch new improvement cycles for your single evolving 3D persona.
        </p>
        <button className="primary" onClick={onBuildPersona}>
          Build My Persona
        </button>
      </section>

      <ViewerPage activeJob={activeJob} />
    </section>
  );
}
