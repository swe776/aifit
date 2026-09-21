// The login token is kept here and sent with every request
let accessToken = null;

// This runs when the login has expired so the user goes back to the log in screen
let onSessionExpired = () => {};


export function setAccessToken(token) {
  accessToken = token;
}


export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler;
}


function plainMessage(error) {
  if (error.loc?.includes("email")) {
    return "Enter a valid email address.";
  }

  return String(error.msg || "").replace(/^Value error, /, "");
}


// Turn the backend's answer into data or message
async function readResponse(response) {
  if (response.status === 204) {
    return null;
  }

  let body = {};

  try {
    body = await response.json();
  } catch {
    body = {};
  }

  if (!response.ok) {
    // A server error is shown as a message
    if (response.status >= 500) {
      const error = new Error(
        "Could not reach AI.FIT. Check that the "
        + "server is running and try again."
      );
      error.status = response.status;

      throw error;
    }

    let message = (
      body.detail || "The request failed."
    );

    // Join many error messages into one line
    if (Array.isArray(message)) {
      message = message
        .map(plainMessage)
        .join(" ");
    }

    const error = new Error(message);
    error.status = response.status;

    throw error;
  }

  return body;
}


// Every call to the backend goes through here
async function request(
  path,
  options = {},
) {
  const headers = new Headers(
    options.headers || {}
  );

  // Send the login token so the backend knows which account is asking
  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`
    );
  }

  let response;

  try {
    response = await fetch(path, {
      ...options,
      headers,
    });
  } catch {
    // The request could not reach the backend at all
    throw new Error(
      "Could not reach AI.FIT. Check that the "
      + "server is running and try again."
    );
  }

  // A refused login means the session has expired
  if (response.status === 401 && accessToken) {
    onSessionExpired();
  }

  return readResponse(response);
}


export function registerAccount(
  email,
  displayName,
  password,
) {
  return request(
    "/api/accounts/register",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        display_name: displayName,
        password,
      }),
    }
  );
}


// The login is sent as a form because that is what the backend login route reads
export function loginAccount(
  email,
  password,
) {
  const loginForm = new URLSearchParams();

  loginForm.append(
    "username",
    email
  );

  loginForm.append(
    "password",
    password
  );

  return request(
    "/api/accounts/login",
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/x-www-form-urlencoded",
      },
      body: loginForm,
    }
  );
}


export function getMyAccount() {
  return request(
    "/api/accounts/me"
  );
}


export function acceptPrivacyNotice() {
  return request(
    "/api/accounts/privacy-notice",
    {
      method: "POST",
    }
  );
}


// Step 1 sends the recording to be turned into a transcript
export function transcribeVoiceEntry(
  audioFile,
) {
  const form = new FormData();

  form.append(
    "audio",
    audioFile.blob,
    audioFile.name || "voice-checkin.webm"
  );

  return request(
    "/api/checkins/transcribe",
    {
      method: "POST",
      body: form,
    }
  );
}


// Step 2 sends the photograph to get the three meal readings
export function readMealPhoto(
  imageFile,
) {
  const form = new FormData();

  form.append(
    "image",
    imageFile,
    imageFile.name
  );

  return request(
    "/api/checkins/analyse-meal",
    {
      method: "POST",
      body: form,
    }
  );
}


// Step 3 sends the checked transcript, the photograph and the band the user picked
export function createCheckin(
  transcript,
  imageFile,
  confirmedMealBand,
) {
  const form = new FormData();

  form.append(
    "transcript",
    transcript
  );

  form.append(
    "image",
    imageFile,
    imageFile.name
  );

  if (confirmedMealBand) {
    form.append(
      "confirmed_nutrition_category",
      confirmedMealBand
    );
  }

  return request(
    "/api/checkins",
    {
      method: "POST",
      body: form,
    }
  );
}


// Only send the parts the user actually corrected
export function correctCheckin(
  checkinId,
  emotionLabel,
  correctedMealBand,
) {
  const correction = {};

  if (emotionLabel) {
    correction.emotion_label = (
      emotionLabel
    );
  }

  if (correctedMealBand) {
    correction.nutrition_category = (
      correctedMealBand
    );
  }

  return request(
    `/api/checkins/${checkinId}/correction`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        correction
      ),
    }
  );
}


export function getCheckins() {
  return request(
    "/api/checkins"
  );
}


// The scores for the risk chart on the dashboard
export function getRiskTrend() {
  return request(
    "/api/checkins/trend"
  );
}


// The numbers shown at the top of the dashboard
export function getDashboardStats() {
  return request(
    "/api/checkins/stats"
  );
}


// Save feedback if the advice helped and any written feedback
export function sendRecommendationFeedback(
  checkinId,
  helpful,
  feedbackText,
) {
  return request(
    `/api/checkins/${checkinId}/feedback`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        helpful,
        feedback_text: (
          feedbackText || null
        ),
      }),
    }
  );
}


export function deleteCheckin(
  checkinId,
) {
  return request(
    `/api/checkins/${checkinId}`,
    {
      method: "DELETE",
    }
  );
}
