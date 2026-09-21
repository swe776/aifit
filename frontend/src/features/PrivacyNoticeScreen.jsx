import { useState } from "react";

import { useAuth } from "../auth.jsx";


// Users must accept the privacy notice before they can use the application
export default function PrivacyNoticeScreen() {
  const {
    acceptPrivacy,
    logout,
  } = useAuth();

  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function continueToApp() {
    setError("");
    setSaving(true);

    try {
      await acceptPrivacy();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="notice-layout">
      <section className="card notice-card">
        <p className="card-label">
          Before the first check-in
        </p>

        <h1>Privacy notice</h1>

        <p>
          AI.FIT uses a short voice recording and meal
          photograph for each check-in.
        </p>

        {/* Explain what happens to the recording and the photograph */}
        <h2>What the application processes</h2>

        <ul>
          <li>
            The voice recording is converted into text.
          </li>
          <li>
            The text is analysed for emotional signals
            linked to fitness dropout.
          </li>
          <li>
            The meal photograph is analysed for visible
            food information.
          </li>
          <li>
            The results are combined to calculate a
            dropout risk score.
          </li>
        </ul>

        {/* Raw uploads are deleted after analysis and only the results are kept */}
        <h2>What the application stores</h2>

        <p>
          The raw voice recording and meal photograph
          are deleted after they are analysed. AI.FIT only
          stores the transcript, model results, dropout
          risk score, recommendations and any feedback
          given by the user.
        </p>

        {/* Users must know that AI.FIT is not a medical tool */}
        <h2>Limitations</h2>

        <p>
          The AI models can make incorrect predictions.
          AI.FIT gives general fitness support and does
          not replace advice from a qualified
          professional.
        </p>

        {/* The user cannot continue until they tick that they have read the notice */}
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(event) =>
              setAccepted(event.target.checked)
            }
          />

          <span>
            I have read and understood the privacy
            notice.
          </span>
        </label>

        {error && (
          <p className="error" aria-live="polite">
            {error}
          </p>
        )}

        <div className="button-row">
          <button
            className="secondary-button"
            type="button"
            onClick={logout}
          >
            Log out
          </button>

          <button
            className="primary-button"
            type="button"
            onClick={continueToApp}
            disabled={!accepted || saving}
          >
            {saving
              ? "Saving..."
              : "Continue to AI.FIT"}
          </button>
        </div>
      </section>
    </main>
  );
}
