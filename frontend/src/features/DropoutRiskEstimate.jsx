function formatLevel(level) {
  return (
    level.charAt(0).toUpperCase()
    + level.slice(1)
  );
}


// Show the dropout score out of 10 with its risk level
export default function DropoutRiskEstimate({
  score,
  level,
}) {
  // Turn the score into how full the bar should be
  const percentage = Math.min(
    Math.max(score * 10, 0),
    100,
  );

  return (
    <section
      className={`risk-estimate risk-${level}`}
      aria-label={
        `${level} dropout risk estimate, `
        + `${score} out of 10`
      }
    >
      <p className="estimate-title">
        Dropout risk estimate
      </p>

      <div className="estimate-value">
        <strong>{score.toFixed(1)}</strong>
        <span>out of 10</span>
      </div>

      <div
        className="estimate-track"
        role="progressbar"
        aria-valuemin="0"
        aria-valuemax="10"
        aria-valuenow={score}
      >
        <span
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>

      <p className="estimate-level">
        {formatLevel(level)} risk
      </p>
    </section>
  );
}
