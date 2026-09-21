import {
  useEffect,
  useRef,
  useState,
} from "react";


// A voice entry can be up to thirty seconds long
const MAX_RECORDING_SECONDS = 30;


// The user can record a voice entry or upload an audio file
export default function VoiceEntryInput({
  onAudioChange,
}) {
  const mediaRecorder = useRef(null);
  const mediaStream = useRef(null);
  const recordedChunks = useRef([]);
  const timer = useRef(null);

  const [recording, setRecording] =
    useState(false);
  const [seconds, setSeconds] = useState(0);
  const [audioPreview, setAudioPreview] =
    useState("");
  const [audioName, setAudioName] =
    useState("");
  const [error, setError] = useState("");

  // Turn off the microphone when the user leaves the screen
  useEffect(() => {
    return () => {
      stopMicrophone();

      if (timer.current) {
        clearInterval(timer.current);
      }
    };
  }, []);

  // Free the old audio preview when a new one replaces it
  useEffect(() => {
    return () => {
      if (audioPreview) {
        URL.revokeObjectURL(audioPreview);
      }
    };
  }, [audioPreview]);

  // Stop using the microphone so the browser no longer shows it as recording
  function stopMicrophone() {
    if (mediaStream.current) {
      mediaStream.current
        .getTracks()
        .forEach((track) => track.stop());

      mediaStream.current = null;
    }
  }

  // Use an audio type this browser can record
  function chooseAudioType() {
    const audioTypes = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
    ];

    return audioTypes.find((audioType) =>
      MediaRecorder.isTypeSupported(audioType)
    );
  }

  function saveAudio(blob, name) {
    const previewUrl = URL.createObjectURL(blob);

    setAudioPreview(previewUrl);
    setAudioName(name);

    onAudioChange({
      blob,
      name,
    });
  }

  // Ask for the microphone and start recording
  async function startRecording() {
    setError("");

    if (
      !navigator.mediaDevices
      || !window.MediaRecorder
    ) {
      setError(
        "Voice recording is not supported by this browser."
      );
      return;
    }

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

      mediaStream.current = stream;
      recordedChunks.current = [];

      const audioType = chooseAudioType();

      mediaRecorder.current = new MediaRecorder(
        stream,
        audioType ? { mimeType: audioType } : {}
      );

      mediaRecorder.current.ondataavailable = (
        event
      ) => {
        if (event.data.size > 0) {
          recordedChunks.current.push(event.data);
        }
      };

      // Save the recording once it stops
      mediaRecorder.current.onstop = () => {
        const fileType =
          mediaRecorder.current.mimeType
          || "audio/webm";

        const extension = fileType.includes("mp4")
          ? "m4a"
          : "webm";

        const audioBlob = new Blob(
          recordedChunks.current,
          { type: fileType }
        );

        saveAudio(
          audioBlob,
          `voice-checkin.${extension}`
        );

        stopMicrophone();
      };

      mediaRecorder.current.start();
      setRecording(true);
      setSeconds(0);

      // Count the seconds and stop automatically at thirty seconds
      timer.current = setInterval(() => {
        setSeconds((currentSeconds) => {
          const nextSecond = currentSeconds + 1;

          if (
            nextSecond >= MAX_RECORDING_SECONDS
            && mediaRecorder.current?.state
              === "recording"
          ) {
            mediaRecorder.current.stop();
            setRecording(false);
            clearInterval(timer.current);
          }

          return nextSecond;
        });
      }, 1000);
    } catch {
      setError(
        "Microphone access was not allowed."
      );
      stopMicrophone();
    }
  }

  function stopRecording() {
    if (
      mediaRecorder.current
      && mediaRecorder.current.state
        === "recording"
    ) {
      mediaRecorder.current.stop();
    }

    if (timer.current) {
      clearInterval(timer.current);
    }

    setRecording(false);
  }

  // An audio file can be uploaded instead of recording
  function uploadAudio(event) {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

    setError("");
    saveAudio(file, file.name);
  }

  // Remove the recording so the user can record again
  function removeAudio() {
    setAudioPreview("");
    setAudioName("");
    setSeconds(0);
    onAudioChange(null);
  }

  return (
    <section className="input-panel">
      <div className="input-heading">
        <div>
          <p className="step-label">Voice entry</p>
          <h2>How has your fitness journey felt?</h2>
        </div>

        <span className="time-limit">
          Up to 30 seconds
        </span>
      </div>

      <p>
        Talk about your motivation, energy or how your
        recent workouts have felt.
      </p>

      {!audioPreview && (
        <div className="input-actions">
          {!recording ? (
            <button
              type="button"
              className="primary-button"
              onClick={startRecording}
            >
              Start recording
            </button>
          ) : (
            <button
              type="button"
              className="stop-button"
              onClick={stopRecording}
            >
              Stop recording ({seconds}s)
            </button>
          )}

          <label className="upload-button">
            Upload audio
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.flac,.ogg,.oga,.webm,audio/*"
              onChange={uploadAudio}
              hidden
            />
          </label>
        </div>
      )}

      {audioPreview && (
        <div className="preview-box">
          <p>{audioName}</p>

          <audio
            controls
            src={audioPreview}
          />

          <button
            type="button"
            className="text-button"
            onClick={removeAudio}
          >
            Remove and record again
          </button>
        </div>
      )}

      {error && (
        <p className="error" aria-live="polite">
          {error}
        </p>
      )}
    </section>
  );
}
