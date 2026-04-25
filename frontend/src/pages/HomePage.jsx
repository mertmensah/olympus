import StepCard from "../components/StepCard";

const STEPS = [
  {
    title: "1. Capture",
    description: "Upload photos and short videos that cover multiple angles and lighting conditions."
  },
  {
    title: "2. Reconstruct",
    description: "Olympus runs a multi-stage AI pipeline to build a faithful 3D likeness."
  },
  {
    title: "3. Preview",
    description: "Open your result in the interactive viewer and request refinements when needed."
  }
];

export default function HomePage({ onStart }) {
  return (
    <section className="hero">
      <p className="eyebrow">Identity Reconstruction</p>
      <h1>Immortalize Your Presence as a 3D Digital Asset</h1>
      <p>
        Olympus helps users transform personal media into a persistent visual likeness suitable for future
        interactive experiences.
      </p>
      <button className="primary" onClick={onStart}>
        Start Upload Flow
      </button>
      <div className="steps-grid">
        {STEPS.map((step) => (
          <StepCard key={step.title} title={step.title} description={step.description} />
        ))}
      </div>
    </section>
  );
}
