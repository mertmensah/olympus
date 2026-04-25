export default function StepCard({ title, description }) {
  return (
    <article className="step-card">
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  );
}
