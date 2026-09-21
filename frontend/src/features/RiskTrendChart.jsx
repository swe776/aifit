// The size of the chart and the space left around it for the labels
const WIDTH = 720;
const HEIGHT = 280;
const LEFT = 50;
const RIGHT = 20;
const TOP = 20;
const BOTTOM = 45;


// Colour each point by its risk level
function pointColour(level) {
  if (level === "high") {
    return "var(--risk-high)";
  }

  if (level === "medium") {
    return "var(--risk-medium)";
  }

  return "var(--risk-low)";
}


function shortDate(date) {
  return new Date(date).toLocaleDateString(
    undefined,
    {
      day: "numeric",
      month: "short",
    }
  );
}


// The dashboard chart of dropout scores over time
export default function RiskTrendChart({ points }) {
  // Nothing is drawn until the user has made a check-in
  if (!points.length) {
    return (
      <p className="empty-message">
        No previous check-ins are available yet.
      </p>
    );
  }

  const chartWidth = WIDTH - LEFT - RIGHT;
  const chartHeight = HEIGHT - TOP - BOTTOM;

  // Spread the check-ins from left to right
  function xPosition(index) {
    if (points.length === 1) {
      return LEFT + chartWidth / 2;
    }

    return (
      LEFT
      + index * chartWidth / (points.length - 1)
    );
  }

  // A higher score is drawn higher on the chart
  function yPosition(score) {
    return TOP + (10 - score) * chartHeight / 10;
  }

  const linePoints = points
    .map((point, index) => (
      `${xPosition(index)},${yPosition(
        point.dropout_risk_score
      )}`
    ))
    .join(" ");

  // Only label the first, middle and last dates so they do not overlap
  const dateIndexes = new Set([
    0,
    Math.floor((points.length - 1) / 2),
    points.length - 1,
  ]);

  return (
    <div className="chart-wrapper">
      <svg
        className="trend-chart"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Dropout risk scores over time"
      >
        {/* Grid lines for the scores from 0 to 10 */}
        {[0, 2, 4, 6, 8, 10].map((score) => {
          const y = yPosition(score);

          return (
            <g key={score}>
              <line
                className="chart-grid-line"
                x1={LEFT}
                y1={y}
                x2={WIDTH - RIGHT}
                y2={y}
              />

              <text
                className="chart-label"
                x={LEFT - 12}
                y={y + 4}
                textAnchor="end"
              >
                {score}
              </text>
            </g>
          );
        })}

        {/* The line is only drawn when there is more than one check-in */}
        {points.length > 1 && (
          <polyline
            className="trend-line"
            points={linePoints}
          />
        )}

        {points.map((point, index) => (
          <g key={`${point.date}-${index}`}>
            <circle
              cx={xPosition(index)}
              cy={yPosition(
                point.dropout_risk_score
              )}
              r="6"
              fill={pointColour(
                point.dropout_risk_level
              )}
            >
              <title>
                {shortDate(point.date)}:{" "}
                {point.dropout_risk_score} out of 10
              </title>
            </circle>

            {dateIndexes.has(index) && (
              <text
                className="chart-label"
                x={xPosition(index)}
                y={HEIGHT - 15}
                textAnchor="middle"
              >
                {shortDate(point.date)}
              </text>
            )}
          </g>
        ))}
      </svg>

      {/* Key for the three risk level colours */}
      <div className="chart-key">
        <span>
          <i className="key-dot low-dot" />
          Low
        </span>

        <span>
          <i className="key-dot medium-dot" />
          Medium
        </span>

        <span>
          <i className="key-dot high-dot" />
          High
        </span>
      </div>
    </div>
  );
}
