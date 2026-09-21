import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import * as api from "./api.js";


const AuthContext = createContext(null);
// The login token is saved in the browser under this name
const TOKEN_KEY = "aifit_login_token";

// Remove a saved transcript so the next user does not see it
function clearSavedTranscript() {
  try {
    sessionStorage.removeItem("aifit.transcript");
  } catch {
  }
}


// Keep track of the logged in user for every screen
export function AuthProvider({ children }) {
  const [account, setAccount] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Log the user out when their session has expired
    api.setSessionExpiredHandler(() => {
      clearSavedTranscript();
      localStorage.removeItem(TOKEN_KEY);
      api.setAccessToken(null);
      setAccount(null);
    });

    // Log the user back in when a saved token is still valid
    const savedToken = localStorage.getItem(TOKEN_KEY);

    if (!savedToken) {
      setReady(true);
      return;
    }

    api.setAccessToken(savedToken);

    api.getMyAccount()
      .then(setAccount)
      // Forget the token when it is no longer valid
      .catch(() => {
        clearSavedTranscript();
        localStorage.removeItem(TOKEN_KEY);
        api.setAccessToken(null);
      })
      .finally(() => setReady(true));
  }, []);

  // Save the token after signing up or logging in
  function saveLogin(result) {
    clearSavedTranscript();
    localStorage.setItem(
      TOKEN_KEY,
      result.access_token
    );

    api.setAccessToken(result.access_token);
    setAccount(result.account);
  }

  async function register(
    email,
    displayName,
    password,
  ) {
    const result = await api.registerAccount(
      email,
      displayName,
      password,
    );

    saveLogin(result);
  }

  async function login(email, password) {
    const result = await api.loginAccount(
      email,
      password,
    );

    saveLogin(result);
  }

  // Logging out removes the token and any saved transcript
  function logout() {
    clearSavedTranscript();
    localStorage.removeItem(TOKEN_KEY);
    api.setAccessToken(null);
    setAccount(null);
  }

  // Save that the user accepted the privacy notice
  async function acceptPrivacy() {
    const updatedAccount =
      await api.acceptPrivacyNotice();

    setAccount(updatedAccount);
  }

  return (
    <AuthContext.Provider
      value={{
        account,
        ready,
        register,
        login,
        logout,
        acceptPrivacy,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


// Any screen can use this to get the logged in user
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider."
    );
  }

  return context;
}
