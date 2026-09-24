import {
  useEffect,
  useState,
} from "react";

import {
  deleteCheckin,
  getCheckins,
  getDashboardStats,
  getRiskTrend,
} from "../api.js";
import RiskTrendChart from "./RiskTrendChart.jsx";


// Show the date and time in the user's own format
function formatDate(date) {
  return new Date(date).toLocaleString(
    undefined,
    {
      dateStyle: "medium",
      timeStyle: "short",
    }
  );
}


// Turn a label like "low motivation" into "Low Motivation"
function formatLabel(label) {
  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}


// Keep the difference at one decimal place without rounding up 1.48 to 1.5
function formatDifference(value) {
  const truncated = Math.trunc(value * 10) / 10;

  return `${truncated > 0 ? "+" : ""}${truncated.toFixed(1)}`;
}


// The heading for each risk change
const RISK_CHANGE_HEADINGS = {
  increasing: "Increasing",
  decreasing: "Decreasing",
  stable: "Stable",
  insufficient: "No baseline yet",
};


// Explain the personal baseline to the user
function baselineMessage(stats) {
  if (stats.trend_direction === "insufficient") {
    return (
      "At least two previous check-ins are needed "
      + "before a personal baseline can be calculated."
    );
  }

  if (stats.trend_direction === "increasing") {
    return (
      "The current dropout risk is higher than "
      + "the personal baseline."
    );
  }

  if (stats.trend_direction === "decreasing") {
    return (
      "The current dropout risk is lower than "
      + "the personal baseline."
    );
  }

  return (
    "The current dropout risk is stable compared "
    + "with the personal baseline."
  );
}


// The dashboard shows the user's scores, personal baseline, risk chart and history
export default function DashboardScreen({
  refreshKey,
  onNewCheckin,
}) {
  const [stats, setStats] = useState(null);
  const [riskTrend, setRiskTrend] = useState([]);
  const [checkins, setCheckins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Load the numbers, the chart and the history together
  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const [
        statsResult,
        trendResult,
        checkinResult,
      ] = await Promise.all([
        getDashboardStats(),
        getRiskTrend(),
        getCheckins(),
      ]);

      setStats(statsResult);
      setRiskTrend(trendResult);
      setCheckins(checkinResult);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  // Load the dashboard again whenever it is opened
  useEffect(() => {
    loadDashboard();
  }, [refreshKey]);

  async function removeCheckin(checkinId) {
    // Ask before deleting because a deleted check-in cannot be brought back
    const confirmed = window.confirm(
      "Delete this check-in?"
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteCheckin(checkinId);
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  if (loading) {
    return (
      <main className="page-content">
        <p>Loading dashboard...</p>
      </main>
    );
  }

  return (
    <main className="page-content">
      <header className="page-heading dashboard-heading">
        <div>
          <p className="card-label">Dashboard</p>
          <h1>Your check-in history</h1>

          <p>
            View previous dropout risk scores and
            compare the latest result with your
            personal baseline.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={onNewCheckin}
        >
          New check-in
        </button>
      </header>

      {error && (
        <p className="error" aria-live="polite">
          {error}
        </p>
      )}

      {stats && (
        <>
          {/* Total check-ins, average risk score and how many were high risk */}
          <section className="stats-grid">
            <article className="stat-card">
              <span>Total check-ins</span>
              <strong>{stats.total_checkins}</strong>
            </article>

            <article className="stat-card">
              <span>Average risk score</span>
              <strong>
                {stats.average_risk_score.toFixed(1)}
              </strong>
            </article>

            <article className="stat-card">
              <span>High-risk check-ins</span>
              <strong>
                {stats.high_risk_checkins}
              </strong>
            </article>
          </section>

          {/* The personal baseline and the risk change */}
          <section className="card baseline-card">
            <div>
              <p className="card-label">
                Personal baseline
              </p>

              <h2>
                {RISK_CHANGE_HEADINGS[stats.trend_direction]}
              </h2>
            </div>

            <p>{baselineMessage(stats)}</p>

            {/* The baseline numbers only show once there are at least two previous scores */}
            {stats.personal_baseline !== null && (
              <dl className="baseline-values">
                <div>
                  <dt>Baseline score</dt>
                  <dd>
                    {stats.personal_baseline.toFixed(1)}
                  </dd>
                </div>

                <div>
                  <dt>Difference</dt>
                  <dd>
                   {formatDifference(stats.difference_from_baseline)}
                  </dd>
                </div>
              </dl>
            )}
          </section>
        </>
      )}

      {/* The chart of risk scores over time */}
      <section className="card chart-card">
        <div className="section-heading">
          <div>
            <p className="card-label">Risk trend</p>
            <h2>Dropout risk over time</h2>
          </div>

          <span>Score from 0 to 10</span>
        </div>

        <RiskTrendChart points={riskTrend} />
      </section>

      {/* Every past check-in with a button to delete it */}
      <section className="history-section">
        <div className="section-heading">
          <div>
            <p className="card-label">History</p>
            <h2>Previous check-ins</h2>
          </div>
        </div>

        {!checkins.length ? (
          <p className="empty-message">
            Complete the first check-in to start
            building a personal baseline.
          </p>
        ) : (
          <div className="history-list">
            {checkins.map((checkin) => (
              <article
                className="card history-card"
                key={checkin.id}
              >
                <div>
                  <p className="history-date">
                    {formatDate(checkin.created_at)}
                  </p>

                  <h3>
                    {formatLabel(
                      checkin.dropout_risk_level
                    )}{" "}
                    risk
                  </h3>

                  <p>
                    Emotional signal:{" "}
                    <strong>
                      {formatLabel(
                        checkin
                          .corrected_emotion_label
                        || checkin.emotion_label
                      )}
                    </strong>

                    {checkin
                      .corrected_emotion_label && (
                      <span className="small-note">
                        {" "}(corrected by you)
                      </span>
                    )}
                  </p>

                  <p>
                    Nutrition band:{" "}
                    <strong>
                      {formatLabel(
                        checkin
                          .corrected_nutrition_category
                        || checkin.nutrition_category
                      )}
                    </strong>

                    {checkin
                      .corrected_nutrition_category && (
                      <span className="small-note">
                        {" "}(corrected by you)
                      </span>
                    )}
                  </p>
                </div>

                <div className="history-score">
                  <strong>
                    {checkin.dropout_risk_score.toFixed(1)}
                  </strong>

                  <span>out of 10</span>

                  <button
                    type="button"
                    className="danger-text-button"
                    onClick={() =>
                      removeCheckin(checkin.id)
                    }
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
