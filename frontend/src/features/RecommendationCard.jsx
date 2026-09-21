// Show the headline and the tips given for a check-in
export default function RecommendationCard({
  headline,
  tips,
}) {
  return (
    <section className="card recommendation-card">
      <p className="card-label">Recommendations</p>

      <h2>{headline}</h2>

      <ul>
        {tips.map((tip, index) => (
          <li key={`${index}-${tip}`}>
            {tip}
          </li>
        ))}
      </ul>
    </section>
  );
}
