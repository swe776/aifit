import { useState } from "react";

import {
  AuthProvider,
  useAuth,
} from "./auth.jsx";
import AccountScreen from "./features/AccountScreen.jsx";
import CheckInResultScreen from "./features/CheckInResultScreen.jsx";
import CheckInScreen from "./features/CheckInScreen.jsx";
import DashboardScreen from "./features/DashboardScreen.jsx";
import PrivacyNoticeScreen from "./features/PrivacyNoticeScreen.jsx";


// The main app shown once the user is logged in and has accepted the privacy notice
function MainApplication() {
  const {
    account,
    logout,
  } = useAuth();

  const [screen, setScreen] =
    useState("checkin");
  const [checkinResult, setCheckinResult] =
    useState(null);

  // Remember which meal reading the user picked so the result screen can show it
  const [chosenReading, setChosenReading] =
    useState(null);
  // Changing this makes the dashboard load the latest check-ins again
  const [refreshKey, setRefreshKey] =
    useState(0);

  // Start a new check-in from an empty screen
  function openNewCheckin() {
    setCheckinResult(null);
    setChosenReading(null);
    setScreen("checkin");
    window.scrollTo(0, 0);
  }

  function openDashboard() {
    setCheckinResult(null);
    setScreen("dashboard");
    setRefreshKey((current) => current + 1);
    window.scrollTo(0, 0);
  }

  // Show the result screen once a check-in has been analysed
  function showCheckinResult(result, reading) {
    setCheckinResult(result);
    setChosenReading(reading || null);
    setRefreshKey((current) => current + 1);
    window.scrollTo(0, 0);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <button
            type="button"
            className="brand"
            onClick={openNewCheckin}
          >
            <span className="brand-mark" />
            AI.FIT
          </button>

          <nav aria-label="Main navigation">
            <button
              type="button"
              className={
                screen === "checkin"
                && !checkinResult
                  ? "nav-button active"
                  : "nav-button"
              }
              onClick={openNewCheckin}
            >
              New check-in
            </button>

            <button
              type="button"
              className={
                screen === "dashboard"
                  ? "nav-button active"
                  : "nav-button"
              }
              onClick={openDashboard}
            >
              Dashboard
            </button>
          </nav>

          <div className="account-menu">
            <span>
              {account.display_name}
            </span>

            <button
              type="button"
              className="text-button"
              onClick={logout}
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      {/* Show the result screen, the dashboard or the check-in screen */}
      {checkinResult ? (
        <CheckInResultScreen
          checkin={checkinResult}
          chosenReading={chosenReading}
          onNewCheckin={openNewCheckin}
          onViewDashboard={openDashboard}
        />
      ) : screen === "dashboard" ? (
        <DashboardScreen
          refreshKey={refreshKey}
          onNewCheckin={openNewCheckin}
        />
      ) : (
        <CheckInScreen
          onCheckinCreated={showCheckinResult}
        />
      )}

      {/* AI.FIT is not a medical tool so this is shown on every screen */}
      <footer className="app-footer">
        <p>
          AI.FIT gives general fitness support. It does
          not substitute for a medical or nutrition diagnosis.
        </p>
      </footer>
    </div>
  );
}


// Decide which screen to show based on the login and the privacy notice
function ScreenForAccount() {
  const {
    account,
    ready,
  } = useAuth();

  if (!ready) {
    return (
      <main className="loading-screen">
        <p>Loading AI.FIT...</p>
      </main>
    );
  }

  // Users who are not logged in see the sign up and log in screen
  if (!account) {
    return <AccountScreen />;
  }

  // Consent is needed before the user can make a check-in
  if (!account.privacy_notice_accepted_at) {
    return <PrivacyNoticeScreen />;
  }

  return <MainApplication />;
}


export default function App() {
  return (
    <AuthProvider>
      <ScreenForAccount />
    </AuthProvider>
  );
}
