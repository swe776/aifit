import { useEffect, useRef, useState } from "react";

import {
  readMealPhoto,
  createCheckin,
  transcribeVoiceEntry,
} from "../api.js";
import MealPhotoInput from "./MealPhotoInput.jsx";
import VoiceEntryInput from "./VoiceEntryInput.jsx";


// Plain headings for the three meal readings instead of the model names
const READING_HEADINGS = {
  dish: "Dish",
  food_group: "Food group",
  caption: "Description",
};


// The check-in screen with the voice entry and the meal photograph
export default function CheckInScreen({
  onCheckinCreated,
}) {
  const SAVED_TRANSCRIPT = "aifit.transcript";

  // A saved transcript is kept if the page reloads so the user does not have to record again
  function readSavedTranscript() {
    try {
      return window.sessionStorage.getItem(SAVED_TRANSCRIPT) || "";
    } catch {
      return "";
    }
  }

  const [audio, setAudio] = useState(null);
  const [transcript, setTranscript] = useState(readSavedTranscript);
  const [restored, setRestored] = useState(
    () => readSavedTranscript() !== ""
  );
  const [transcriptReady, setTranscriptReady] =
    useState(() => readSavedTranscript() !== "");
  const [transcriptWarning, setTranscriptWarning] =
    useState(false);
  const [transcriptSaved, setTranscriptSaved] =
    useState(() => readSavedTranscript() !== "");
  const [image, setImage] = useState(null);

  const [transcribing, setTranscribing] =
    useState(false);
  const [analysing, setAnalysing] =
    useState(false);

  const [mealReading, setMealReading] =
    useState(null);
  const [mealBand, setMealBand] =
    useState("");

  // Which of the three readings the user tapped
  const [chosenReadingSource, setChosenReadingSource] =
    useState("");

  const [pickingBand, setPickingBand] =
    useState(false);
  const [readingMeal, setReadingMeal] =
    useState(false);

  // Stops the check-in from being sent twice
  const submitting = useRef(false);
  // Ignore an answer that comes back for a recording or photograph the user has already replaced
  const audioVersion = useRef(0);
  const imageVersion = useRef(0);
  const [error, setError] = useState("");

  // A new recording needs a new transcript
  function changeAudio(nextAudio) {
    audioVersion.current += 1;
    setAudio(nextAudio);
    setTranscript("");
    setTranscriptReady(false);
    setTranscriptWarning(false);
    setTranscriptSaved(false);
    setError("");
  }

  // Save the transcript for this browser tab once the user has checked it
  useEffect(() => {
    try {
      if (transcriptSaved && transcript) {
        window.sessionStorage.setItem(
          SAVED_TRANSCRIPT,
          transcript
        );
      } else if (!transcriptSaved) {
        window.sessionStorage.removeItem(SAVED_TRANSCRIPT);
      }
    } catch {
    }
  }, [transcript, transcriptSaved]);

  function forgetSavedTranscript() {
    try {
      window.sessionStorage.removeItem(SAVED_TRANSCRIPT);
    } catch {
    }
  }

  // Tapping a reading uses its band for the check-in
  function pickFoodReading(foodReading) {
    setMealBand(foodReading.band);
    setChosenReadingSource(foodReading.source);
  }

  // A new photograph needs to be read again
  function changeImage(nextImage) {
    imageVersion.current += 1;
    setImage(nextImage);
    setMealReading(null);
    setMealBand("");
    setChosenReadingSource("");
    setPickingBand(false);
    setError("");
  }

  // Step 2 gets the three meal readings for the photograph
  async function showMealReadings() {
    setError("");

    if (!image) {
      setError(
        "Take or upload a meal photograph first."
      );
      return;
    }

    setReadingMeal(true);
    const version = imageVersion.current;

    try {
      const reading =
        await readMealPhoto(image);

      // The user changed the photograph while it was being read
      if (version !== imageVersion.current) return;

      setMealReading(reading);
      setChosenReadingSource("");
      setPickingBand(false);

      setMealBand("");
    } catch (requestError) {
      if (version === imageVersion.current) setError(requestError.message);
    } finally {
      setReadingMeal(false);
    }
  }

  function changeTranscript(event) {
    setTranscript(event.target.value);
    setTranscriptSaved(false);
    setError("");
  }

  // Step 1 turns the voice entry into a transcript
  async function createTranscript() {
    if (!audio) {
      setError(
        "Record or upload a voice entry first."
      );
      return;
    }

    setError("");
    setTranscribing(true);
    setTranscriptSaved(false);

    const version = audioVersion.current;
    try {
      const result = await transcribeVoiceEntry(
        audio
      );

      if (version !== audioVersion.current) return;
      setTranscript(result.transcript);
      setTranscriptReady(true);
      // Warn the user when the transcript does not sound like a check-in
      setTranscriptWarning(
        result.looks_relevant === false
      );
    } catch (requestError) {
      if (version === audioVersion.current) setError(requestError.message);
    } finally {
      setTranscribing(false);
    }
  }

  // The transcript has to be checked and saved before the check-in can be analysed
  function saveTranscript() {
    const checkedTranscript = transcript.trim();

    if (!checkedTranscript) {
      setError("The transcript cannot be empty.");
      return;
    }

    setTranscript(checkedTranscript);
    setTranscriptSaved(true);
    setError("");
  }

  // Step 3 analyses the check-in once every part is ready
  async function submitCheckin() {
    setError("");

    if (!transcriptReady) {
      setError(
        "Convert the voice entry into text first."
      );
      return;
    }

    if (!transcriptSaved) {
      setError(
        "Check and save the transcript first."
      );
      return;
    }

    if (!image) {
      setError(
        "Take or upload a meal photograph first."
      );
      return;
    }

    if (!mealBand) {
      setError(
        "Check the meal reading and confirm it first."
      );
      return;
    }

    // Do nothing if the check-in is already being sent
    if (submitting.current) {
      return;
    }

    submitting.current = true;
    setAnalysing(true);

    try {
      const result = await createCheckin(
        transcript,
        image,
        mealBand,
      );

      // The saved transcript is no longer needed once the check-in is made
      forgetSavedTranscript();

      onCheckinCreated(
        result,
        mealReading?.food_candidates?.find(
          (foodReading) => foodReading.source === chosenReadingSource
        ) || null,
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      submitting.current = false;
      setAnalysing(false);
    }
  }

  // List what the user still has to do so the button is never greyed out without a reason
  const stepsLeft = [];

  if (!audio) {
    stepsLeft.push(
      "Record or upload a voice entry."
    );
  } else if (!transcriptReady) {
    stepsLeft.push(
      "Create the transcript from your voice entry."
    );
  } else if (!transcriptSaved) {
    stepsLeft.push(
      "Check the transcript and save it."
    );
  }

  if (!image) {
    stepsLeft.push(
      "Take or upload a meal photograph."
    );
  } else if (!mealReading) {
    stepsLeft.push(
      "Read the meal photograph."
    );
  } else if (!mealBand) {
    stepsLeft.push(
      "Tap the reading that matches your food, or pick a band."
    );
  }

  return (
    <main className="page-content">
      <header className="page-heading">
        <p className="card-label">
          New check-in
        </p>

        <h1>
          Complete both parts of the check-in
        </h1>

        <p>
          The voice entry and meal photograph are
          analysed together to calculate the estimated dropout
          risk.
        </p>
      </header>

      <div className="checkin-grid">
        <div className="voice-input-column">
          <VoiceEntryInput
            onAudioChange={changeAudio}
          />

          {/* Offer to turn the voice entry into a transcript */}
          {audio && !transcriptReady && (
            <section className="card transcript-editor">
              <p className="step-label">
                Voice transcript
              </p>

              <h2>
                Convert the voice entry into text
              </h2>

              <p>
                Your voice entry is turned into a
                transcript that you can check before
                anything is scored.
              </p>

              <button
                type="button"
                className="secondary-button"
                onClick={createTranscript}
                disabled={transcribing}
              >
                {transcribing
                  ? "Creating transcript..."
                  : "Create transcript"}
              </button>

              {transcribing && (
                <p className="small-note">
                  The first transcript takes longer,
                  while everything is getting ready.
                </p>
              )}
            </section>
          )}

          {/* The user can check and correct the transcript before anything is scored */}
          {transcriptReady && (
            <section className="card transcript-editor">
              <p className="step-label">
                Voice transcript
              </p>

              <h2>Check the transcript</h2>

              <p>
                If anything is wrong, click inside the
                box, edit it, then save the transcript.
              </p>

              {/* This only warns the user and they can still carry on */}
              {transcriptWarning && (
                <p className="transcript-warning">
                  This did not sound like it was about
                  your training or how you are feeling.
                  Check the transcript is right. You can
                  still save it and carry on.
                </p>
              )}

              <label
                className="transcript-label"
                htmlFor="voice-transcript"
              >
                Transcript
              </label>

              <textarea
                id="voice-transcript"
                value={transcript}
                onChange={changeTranscript}
                rows="7"
                maxLength="2000"
              />

              <p className="character-count">
                {transcript.length}/2000 characters
              </p>

              <div className="transcript-buttons">
                <button
                  type="button"
                  className="primary-button"
                  onClick={saveTranscript}
                  disabled={transcribing}
                >
                  {transcriptSaved
                    ? "Transcript saved"
                    : "Save transcript"}
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={createTranscript}
                  disabled={transcribing}
                >
                  {transcribing
                    ? "Creating transcript..."
                    : "Create transcript again"}
                </button>
              </div>

              {transcriptSaved && (
                <p
                  className="transcript-saved"
                  aria-live="polite"
                >
                  Transcript saved. You can continue with
                  the check-in.
                </p>
              )}
            </section>
          )}
        </div>

        <div className="meal-input-column">
          <MealPhotoInput
            onImageChange={changeImage}
          />

          {image && !mealReading && (
            <section className="meal-reading">
              <button
                type="button"
                className="primary-button"
                onClick={showMealReadings}
                disabled={readingMeal}
              >
                {readingMeal
                  ? "Reading the meal..."
                  : "Read the meal photograph"}
              </button>
            </section>
          )}

          {/* Show the three readings for the user to tap the one that matches their meal */}
          {mealReading && (
            <section className="meal-reading">
              <p className="step-label">
                Confirm the meal
              </p>

              <p className="hint">
                Here is what was read from your
                photograph. Tap whichever one matches
                what you ate.
              </p>

              {mealReading.food_candidates
                ?.length > 0 && (
                <ul className="food-readings">
                  {mealReading.food_candidates.map(
                    (foodReading) => (
                      <li
                        key={foodReading.source}
                        className={
                          !foodReading.band
                            ? "food-reading"
                            : chosenReadingSource ===
                              foodReading.source
                            ? "food-reading pickable selected"
                            : "food-reading pickable"
                        }
                        onClick={
                          foodReading.band
                            ? () =>
                                pickFoodReading(foodReading)
                            : undefined
                        }
                        onKeyDown={
                          foodReading.band
                            ? (event) => {
                                if (
                                  event.key ===
                                    "Enter" ||
                                  event.key === " "
                                ) {
                                  event.preventDefault();
                                  pickFoodReading(foodReading);
                                }
                              }
                            : undefined
                        }
                        role={
                          foodReading.band
                            ? "button"
                            : undefined
                        }
                        tabIndex={
                          foodReading.band ? 0 : undefined
                        }
                      >
                        <span className="food-reading-source">
                          {READING_HEADINGS[foodReading.source]}
                        </span>
                        <span className="food-reading-label">
                          {foodReading.label}
                          {/* A reading the food table cannot place is shown as not sure and cannot be tapped */}
                          {foodReading.band ? (
                            <span className="food-reading-band">
                              {foodReading.band}
                            </span>
                          ) : (
                            <span className="food-reading-band unsure">
                              not sure
                            </span>
                          )}
                        </span>
                      </li>
                    ),
                  )}
                </ul>
              )}

              {!pickingBand && (
                <button
                  type="button"
                  className="text-button meal-none-match"
                  onClick={() => {
                    setPickingBand(true);
                    setChosenReadingSource("");
                    setMealBand("");
                  }}
                >
                  Not your food? Pick a nutrition band
                </button>
              )}

              {/* The user can set the band themselves when no reading matches */}
              {pickingBand && (
                <>
                  <p className="hint">
                    Choose the band that best describes
                    your meal.
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
                          mealBand === value
                            ? "meal-choice selected"
                            : "meal-choice"
                        }
                      >
                        <input
                          type="radio"
                          name="meal-band"
                          value={value}
                          checked={
                            mealBand === value
                          }
                          onChange={() => {
                            setMealBand(value);
                            setChosenReadingSource("");
                          }}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </>
              )}
            </section>
          )}
        </div>
      </div>

      {/* Tell the user their transcript was kept from before the page reloaded */}
      {restored && (
        <p className="success" role="status">
          Your transcript was saved before the page reloaded so you
          do not need to record again. Check if it still looks right.{" "}
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setRestored(false);
              setTranscript("");
              setTranscriptReady(false);
              setTranscriptSaved(false);
              forgetSavedTranscript();
            }}
          >
            Start again
          </button>
        </p>
      )}

      {error && (
        <p className="error" aria-live="polite">
          {error}
        </p>
      )}

      <div className="submit-area">
        <button
          type="button"
          className="primary-button large-button"
          onClick={submitCheckin}
          disabled={
            analysing ||
            transcribing ||
            !transcriptSaved ||
            !image ||
            !mealBand
          }
        >
          {analysing
            ? "Analysing check-in..."
            : "Analyse check-in"}
        </button>

        {!analysing && stepsLeft.length > 0 && (
          <div aria-live="polite">
            <p>
              Still to do before this check-in can be
              analysed:
            </p>

            <ul className="steps-left">
              {stepsLeft.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Show what is happening while the check-in is being analysed */}
        {analysing && (
          <div
            className="analysing-steps"
            aria-live="polite"
          >
            <p>Analysing your check-in:</p>

            <ul className="steps-left">
              <li>
                Reading the emotional signal from your
                transcript
              </li>
              <li>
                Checking your photograph shows a meal
              </li>
              <li>
                Analysing the food and calculating
                your dropout risk
              </li>
            </ul>

            <p className="small-note">
              This takes about ten seconds or longer
              on the first check-in while the models
              are loaded.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
