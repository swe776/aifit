import { useState } from "react";

import { useAuth } from "../auth.jsx";


// The sign up and log in screen
export default function AccountScreen() {
  const {
    register,
    login,
  } = useAuth();

  // The screen opens on log in and the user can switch to creating an account
  const [mode, setMode] = useState("login");
  const [displayName, setDisplayName] =
    useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] =
    useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] =
    useState(false);

  const creatingAccount = mode === "register";

  function changeMode(nextMode) {
    setMode(nextMode);
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    // Check that both passwords match before an account is created
    if (
      creatingAccount
      && password !== confirmPassword
    ) {
      setError("The passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      if (creatingAccount) {
        await register(
          email,
          displayName,
          password,
        );
      } else {
        await login(email, password);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout">
      {/* Explain what AI.FIT does before the user signs up */}
      <section className="auth-intro">
        <p className="card-label">AI.FIT</p>

        <h1>Check your fitness dropout risk.</h1>

        <p>
          AI.FIT analyses a short voice entry and meal
          photograph to give a dropout risk score.
          Previous scores are used to show if the risk
          is increasing, decreasing or stable.
        </p>

        <p className="medical-note">
          AI.FIT gives general fitness support. It does
          not substitute for a medical or nutrition diagnosis.
        </p>
      </section>

      <form
        className="card auth-card"
        onSubmit={handleSubmit}
      >
        {/* Tabs to switch between logging in and creating an account */}
        <div className="auth-tabs">
          <button
            type="button"
            className={
              mode === "login"
                ? "auth-tab active"
                : "auth-tab"
            }
            onClick={() => changeMode("login")}
          >
            Log in
          </button>

          <button
            type="button"
            className={
              creatingAccount
                ? "auth-tab active"
                : "auth-tab"
            }
            onClick={() => changeMode("register")}
          >
            Create account
          </button>
        </div>

        <h2>
          {creatingAccount
            ? "Create an account"
            : "Log in to AI.FIT"}
        </h2>

        {/* A display name is only asked for when creating an account */}
        {creatingAccount && (
          <label>
            Display name
            <input
              type="text"
              value={displayName}
              onChange={(event) =>
                setDisplayName(event.target.value)
              }
              minLength="2"
              maxLength="120"
              autoComplete="name"
              required
            />
          </label>
        )}

        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            autoComplete="email"
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            minLength="8"
            autoComplete={
              creatingAccount
                ? "new-password"
                : "current-password"
            }
            required
          />
        </label>

        {/* The password is typed twice when creating an account */}
        {creatingAccount && (
          <label>
            Confirm password
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) =>
                setConfirmPassword(
                  event.target.value
                )
              }
              minLength="8"
              autoComplete="new-password"
              required
            />
          </label>
        )}

        {error && (
          <p className="error" aria-live="polite">
            {error}
          </p>
        )}

        <button
          className="primary-button"
          type="submit"
          disabled={submitting}
        >
          {submitting
            ? "Please wait..."
            : creatingAccount
              ? "Create account"
              : "Log in"}
        </button>
      </form>
    </main>
  );
}
