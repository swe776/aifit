import { useState } from "react";

import {
  correctCheckin,
  sendRecommendationFeedback,
} from "../api.js";
import DropoutRiskEstimate from "./DropoutRiskEstimate.jsx";
import RecommendationCard from "./RecommendationCard.jsx";


// One plain sentence for each risk level
const RISK_SUMMARIES = {
  low: "Your current dropout risk is low.",
  medium: "Your current dropout risk is medium.",
  high: "Your current dropout risk is high.",
};


// The five emotional signals the user can pick when correcting the result
const EMOTIONAL_SIGNAL_OPTIONS = [
  {
    value: "burnout",
    label: "Burnout",
  },
  {
    value: "low motivation",
    label: "Low motivation",
  },
  {
    value: "fatigue",
    label: "Fatigue",
  },
  {
    value: "high motivation",
    label: "High motivation",
  },
  {
    value: "neutral",
    label: "Neutral",
  },
];


function formatLabel(label) {
  if (!label) {
    return "Not identified";
  }

  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}


// Show a confidence score as a percentage
function formatConfidence(confidence) {
  return `${Math.round(confidence * 100)}%`;
}


// Plain headings for the three meal readings instead of the model names
const READING_HEADINGS = {
  dish: "Dish",
  food_group: "Food group",
  caption: "Description",
};


// The result screen shows the dropout score, the analysis and the recommendations
export default function CheckInResultScreen({
  checkin,
  chosenReading,
  onViewDashboard,
  onNewCheckin,
}) {
  const [currentCheckin, setCurrentCheckin] =
    useState(checkin);

  const [correctionOpen, setCorrectionOpen] =
    useState(false);

  const [
    correctedEmotion,
    setCorrectedEmotion,
  ] = useState(
    checkin.corrected_emotion_label || ""
  );

  const [
    correctedBand,
    setCorrectedBand,
  ] = useState("");

  const [
    savingCorrection,
    setSavingCorrection,
  ] = useState(false);

  const [
    correctionSaved,
    setCorrectionSaved,
  ] = useState(false);

  const [
    correctionError,
    setCorrectionError,
  ] = useState("");

  const [helpful, setHelpful] = useState(
    checkin.recommendation_helpful ?? null
  );

  const [feedbackText, setFeedbackText] =
    useState(
      checkin.feedback_text || ""
    );

  const [
    savingFeedback,
    setSavingFeedback,
  ] = useState(false);

  const [
    feedbackSaved,
    setFeedbackSaved,
  ] = useState(false);

  const [
    feedbackError,
    setFeedbackError,
  ] = useState("");

  // Low risk check-ins with nothing to warn about get no advice
  const hasRecommendation = Boolean(
    currentCheckin.recommendation_headline
  );

  // Show the corrected signal and band when the user has changed them
  const displayedEmotion = (
    currentCheckin.corrected_emotion_label
    || currentCheckin.emotion_label
  );

  const displayedFood = currentCheckin.food_label;

  const displayedMealBand = (
    currentCheckin
      .corrected_nutrition_category
    || currentCheckin.nutrition_category
  );

  // Send the correction so the score, risk level and advice are worked out again
  async function saveCorrection() {
    if (
      !correctedEmotion
      && !correctedBand
    ) {
      setCorrectionError(
        "Correct at least one detected result."
      );
      return;
    }

    setCorrectionError("");
    setCorrectionSaved(false);
    setSavingCorrection(true);

    try {
      const updatedCheckin = (
        await correctCheckin(
          currentCheckin.id,
          correctedEmotion || null,
          correctedBand || null,
        )
      );

      setCurrentCheckin(updatedCheckin);

      setCorrectedEmotion(
        updatedCheckin.corrected_emotion_label
        || ""
      );

      setHelpful(
        updatedCheckin
          .recommendation_helpful
        ?? null
      );

      setFeedbackText(
        updatedCheckin.feedback_text || ""
      );

      setFeedbackSaved(false);
      setCorrectionSaved(true);
      setCorrectionOpen(false);
    } catch (requestError) {
      setCorrectionError(
        requestError.message
      );
    } finally {
      setSavingCorrection(false);
    }
  }

  // Save feedback if the advice was useful and any written feedback was given
  async function saveFeedback() {
    if (helpful === null) {
      setFeedbackError(
        "Select yes or no before saving feedback."
      );
      return;
    }

    setFeedbackError("");
    setSavingFeedback(true);

    try {
      await sendRecommendationFeedback(
        currentCheckin.id,
        helpful,
        feedbackText,
      );

      setFeedbackSaved(true);
    } catch (requestError) {
      setFeedbackError(
        requestError.message
      );
    } finally {
      setSavingFeedback(false);
    }
  }

  return (
    <main className="page-content">
      <header className="page-heading">
        <p className="card-label">
          Check-in result
        </p>

        <h1>Your dropout risk estimate</h1>
      </header>

      <section className="result-summary">
        <DropoutRiskEstimate
          score={
            currentCheckin.dropout_risk_score
          }
          level={
            currentCheckin.dropout_risk_level
          }
        />

        <div>
          <h2>
            {
              RISK_SUMMARIES[
                currentCheckin
                  .dropout_risk_level
              ]
            }
          </h2>

          <p>
            This score combines the emotional signal
            from the voice entry with the nutrition
            signal from the meal photograph.
          </p>
        </div>
      </section>

      {correctionSaved && (
        <p
          className="success"
          aria-live="polite"
        >
          Your correction was saved and the result
          was updated where applicable.
        </p>
      )}

      <section className="analysis-grid">
        {/* The transcript that was analysed */}
        <article className="card analysis-card">
          <p className="card-label">
            Speech to text
          </p>

          <h2>Voice transcript</h2>

          <blockquote>
            &ldquo;{currentCheckin.transcript}&rdquo;
          </blockquote>
        </article>

        {/* The emotional signal with its confidence score */}
        <article className="card analysis-card">
          <p className="card-label">
            Emotional signal
          </p>

          <h2>
            {formatLabel(
              displayedEmotion
            )}
          </h2>

          {currentCheckin
            .corrected_emotion_label ? (
            <>
              <p className="success">
                Corrected by you
              </p>

              <p className="small-note">
                Originally detected as{" "}
                <strong>
                  {formatLabel(
                    currentCheckin
                      .emotion_label
                  )}
                </strong>
                {" "}with{" "}
                {formatConfidence(
                  currentCheckin
                    .emotion_confidence
                )}
                {" "}confidence.
              </p>
            </>
          ) : (
            <p>
              Model confidence:{" "}
              {formatConfidence(
                currentCheckin
                  .emotion_confidence
              )}
            </p>
          )}

          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setCorrectionOpen(true);
              setCorrectionSaved(false);
              setCorrectionError("");
            }}
          >
            Wrong emotional signal?
          </button>
        </article>

        {/* The meal reading the user picked or the band they set themselves */}
        <article className="card analysis-card">
          <p className="card-label">
            {chosenReading
              ? "The reading you picked"
              : "Food recognition"}
          </p>

          <h2>
            {chosenReading
              ? READING_HEADINGS[chosenReading.source]
              : formatLabel(displayedFood)}
          </h2>

          {chosenReading ? (
            <>
              <p>
                {chosenReading.source === "caption"
                  ? chosenReading.label
                  : formatLabel(chosenReading.label)}
              </p>

              {chosenReading.confidence > 0 && (
                <p>
                  Model confidence:{" "}
                  {formatConfidence(
                    chosenReading.confidence
                  )}
                </p>
              )}
            </>
          ) : (
            <p className="small-note">
              You set the nutrition band yourself
              rather than picking a reading.
            </p>
          )}
        </article>

        {/* The nutrition band used for the score */}
        <article className="card analysis-card">
          <p className="card-label">
            Nutrition analysis
          </p>

          <h2>
            {formatLabel(
              displayedMealBand
            )}
          </h2>

          {currentCheckin
            .corrected_nutrition_category ? (
            <p className="success">
              Updated to the nutrition band you picked.
            </p>
          ) : (
            <p className="small-note">
              This is the nutrition band you confirmed
              for this check-in.
            </p>
          )}

          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setCorrectionOpen(true);
              setCorrectionSaved(false);
              setCorrectionError("");
            }}
          >
            Wrong nutrition band?
          </button>
        </article>
      </section>

      {/* The user can correct the emotional signal or the nutrition band here */}
      {correctionOpen && (
        <section className="card correction-card">
          <p className="card-label">
            Correct detected results
          </p>

          <h2>
            Tell us what was detected incorrectly
          </h2>

          <p>
            Correcting the emotional signal or the
            nutrition band updates the dropout risk
            score and the recommendations.
          </p>

          <label htmlFor="corrected-emotion">
            Correct emotional signal
          </label>

          <select
            id="corrected-emotion"
            value={correctedEmotion}
            onChange={(event) => {
              setCorrectedEmotion(
                event.target.value
              );
              setCorrectionSaved(false);
              setCorrectionError("");
            }}
          >
            <option value="">
              Keep the detected signal
            </option>

            {EMOTIONAL_SIGNAL_OPTIONS.map(
              (option) => (
                <option
                  key={option.value}
                  value={option.value}
                >
                  {option.label}
                </option>
              )
            )}
          </select>

          <p className="field-label">
            Nutrition band
          </p>

          <div
            className="meal-choices"
            role="radiogroup"
            aria-label="Nutrition band"
          >
            {[
              ["balanced", "Balanced"],
              ["mixed", "Mixed"],
              ["poor", "Poor"],
            ].map(([value, label]) => (
              <label
                key={value}
                className={
                  correctedBand === value
                    ? "meal-choice selected"
                    : "meal-choice"
                }
              >
                <input
                  type="radio"
                  name="corrected-band"
                  value={value}
                  checked={correctedBand === value}
                  onChange={() => {
                    setCorrectedBand(value);
                    setCorrectionSaved(false);
                    setCorrectionError("");
                  }}
                />
                {label}
                {value ===
                  displayedMealBand && (
                  <span className="detected-tag">
                    now
                  </span>
                )}
              </label>
            ))}
          </div>

          {correctionError && (
            <p
              className="error"
              aria-live="polite"
            >
              {correctionError}
            </p>
          )}

          <div className="button-row">
            <button
              type="button"
              className="secondary-button"
              onClick={() => {
                setCorrectionOpen(false);
                setCorrectionError("");
              }}
              disabled={savingCorrection}
            >
              Cancel
            </button>

            <button
              type="button"
              className="primary-button"
              onClick={saveCorrection}
              disabled={savingCorrection}
            >
              {savingCorrection
                ? "Saving correction..."
                : "Save correction"}
            </button>
          </div>
        </section>
      )}

      {/* The recommendations can be rated and any feedback can be given here */}
      {hasRecommendation && (
        <>
          <RecommendationCard
            headline={
              currentCheckin
                .recommendation_headline
            }
            tips={
              currentCheckin
                .recommendation_tips
            }
          />

          <section className="card feedback-card">
            <p className="card-label">
              Recommendation feedback
            </p>

            <h2>
              Was this recommendation useful?
            </h2>

            <div className="choice-row">
              <button
                type="button"
                className={
                  helpful === true
                    ? "choice-button selected"
                    : "choice-button"
                }
                aria-pressed={
                  helpful === true
                }
                onClick={() => {
                  setHelpful(true);
                  setFeedbackSaved(false);
                }}
              >
                Yes
              </button>

              <button
                type="button"
                className={
                  helpful === false
                    ? "choice-button selected"
                    : "choice-button"
                }
                aria-pressed={
                  helpful === false
                }
                onClick={() => {
                  setHelpful(false);
                  setFeedbackSaved(false);
                }}
              >
                No
              </button>
            </div>

            <label>
              Additional feedback (optional)

              <textarea
                value={feedbackText}
                onChange={(event) => {
                  setFeedbackText(
                    event.target.value
                  );
                  setFeedbackSaved(false);
                }}
                maxLength="500"
                rows="4"
              />
            </label>

            {feedbackError && (
              <p
                className="error"
                aria-live="polite"
              >
                {feedbackError}
              </p>
            )}

            {feedbackSaved && (
              <p
                className="success"
                aria-live="polite"
              >
                Feedback saved.
              </p>
            )}

            <button
              type="button"
              className="secondary-button"
              onClick={saveFeedback}
              disabled={savingFeedback}
            >
              {savingFeedback
                ? "Saving..."
                : "Save feedback"}
            </button>
          </section>
        </>
      )}

      <div className="button-row result-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={onNewCheckin}
        >
          New check-in
        </button>

        <button
          type="button"
          className="primary-button"
          onClick={onViewDashboard}
        >
          View dashboard
        </button>
      </div>
    </main>
  );
}
