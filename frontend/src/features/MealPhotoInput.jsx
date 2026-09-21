import {
  useEffect,
  useRef,
  useState,
} from "react";


// Images are limited to 15 MB like the backend
const MAX_IMAGE_SIZE = 15 * 1024 * 1024;


// The user can take a meal photograph with the camera or upload one
export default function MealPhotoInput({
  onImageChange,
}) {
  const video = useRef(null);
  const canvas = useRef(null);
  const cameraStream = useRef(null);

  const [cameraOpen, setCameraOpen] =
    useState(false);
  const [cameraReady, setCameraReady] =
    useState(false);
  const [imagePreview, setImagePreview] =
    useState("");
  const [imageName, setImageName] =
    useState("");
  const [error, setError] = useState("");

  // Turn off the camera when the user leaves the screen
  useEffect(() => {
    return () => {
      if (cameraStream.current) {
        cameraStream.current
          .getTracks()
          .forEach((track) => track.stop());
      }
    };
  }, []);

  // Free the old photograph preview when a new one replaces it
  useEffect(() => {
    return () => {
      if (imagePreview) {
        URL.revokeObjectURL(imagePreview);
      }
    };
  }, [imagePreview]);

  // Show the camera once it has opened
  useEffect(() => {
    if (
      !cameraOpen ||
      !video.current ||
      !cameraStream.current
    ) {
      return;
    }

    const videoElement = video.current;

    // The photograph button only works once the camera is showing a picture
    function cameraHasLoaded() {
      if (
        videoElement.videoWidth > 0 &&
        videoElement.videoHeight > 0
      ) {
        setCameraReady(true);
        setError("");
      }
    }

    videoElement.srcObject =
      cameraStream.current;

    videoElement.addEventListener(
      "loadedmetadata",
      cameraHasLoaded
    );
    videoElement.addEventListener(
      "canplay",
      cameraHasLoaded
    );

    videoElement
      .play()
      .then(cameraHasLoaded)
      .catch(() => {
        setError(
          "The camera preview could not be started."
        );
      });

    return () => {
      videoElement.removeEventListener(
        "loadedmetadata",
        cameraHasLoaded
      );
      videoElement.removeEventListener(
        "canplay",
        cameraHasLoaded
      );
    };
  }, [cameraOpen]);

  // Stop using the camera so the browser no longer shows it as on
  function stopCamera() {
    if (video.current) {
      video.current.srcObject = null;
    }

    if (cameraStream.current) {
      cameraStream.current
        .getTracks()
        .forEach((track) => track.stop());

      cameraStream.current = null;
    }

    setCameraReady(false);
    setCameraOpen(false);
  }

  // Check the file is an image under 15 MB before it is used
  function saveImage(file) {
    if (!file.type.startsWith("image/")) {
      setError("Choose a photograph file.");
      return;
    }

    if (file.size > MAX_IMAGE_SIZE) {
      setError("The photograph must be smaller than 15 MB.");
      return;
    }

    const previewUrl = URL.createObjectURL(file);

    setImagePreview(previewUrl);
    setImageName(file.name);
    setError("");
    onImageChange(file);
  }

  // Use the back camera on a phone when there is one
  async function openCamera() {
    setError("");
    setCameraReady(false);

    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        "Camera access is not supported by this browser."
      );
      return;
    }

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: {
              ideal: "environment",
            },
          },
          audio: false,
        });

      cameraStream.current = stream;
      setCameraOpen(true);
    } catch {
      setError("Camera access was not allowed.");
      stopCamera();
    }
  }

  // Take a photograph from the camera picture and save it as a JPEG file
  function takePhoto() {
    if (
      !cameraReady ||
      !video.current ||
      !canvas.current
    ) {
      setError("Wait for the camera to finish loading.");
      return;
    }

    const width = video.current.videoWidth;
    const height = video.current.videoHeight;

    canvas.current.width = width;
    canvas.current.height = height;

    const context =
      canvas.current.getContext("2d");

    if (!context) {
      setError(
        "The photograph could not be created."
      );
      return;
    }

    context.drawImage(
      video.current,
      0,
      0,
      width,
      height,
    );

    canvas.current.toBlob(
      (blob) => {
        if (!blob) {
          setError(
            "The photograph could not be saved."
          );
          return;
        }

        const imageFile = new File(
          [blob],
          "meal-photograph.jpg",
          {
            type: "image/jpeg",
          }
        );

        saveImage(imageFile);
        stopCamera();
      },
      "image/jpeg",
      0.9,
    );
  }

  // A photograph can be uploaded instead of taken
  function uploadImage(event) {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

    saveImage(file);
    event.target.value = "";
  }

  // Remove the photograph so the user can choose another one
  function removeImage() {
    setImagePreview("");
    setImageName("");
    setError("");
    onImageChange(null);
  }

  return (
    <section className="input-panel">
      <div className="input-heading">
        <div>
          <p className="step-label">
            Meal photograph
          </p>

          <h2>
            Add a photograph of a recent meal
          </h2>
        </div>
      </div>

      <p>
        AI.FIT uses the meal photo as supporting information
        when calculating dropout risk.
      </p>

      {/* Show the camera and upload buttons until a photograph is chosen */}
      {!imagePreview && !cameraOpen && (
        <div className="input-actions">
          <button
            type="button"
            className="primary-button"
            onClick={openCamera}
          >
            Open camera
          </button>

          <label className="upload-button">
            Upload photograph
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/*"
              onChange={uploadImage}
              hidden
            />
          </label>
        </div>
      )}

      {/* Show the live camera while it is open */}
      {cameraOpen && (
        <div className="camera-box">
          <video
            ref={video}
            muted
            playsInline
          />

          <div className="button-row">
            <button
              type="button"
              className="secondary-button"
              onClick={stopCamera}
            >
              Cancel
            </button>

            <button
              type="button"
              className="primary-button"
              onClick={takePhoto}
              disabled={!cameraReady}
            >
              {cameraReady
                ? "Take photograph"
                : "Starting camera..."}
            </button>
          </div>
        </div>
      )}

      <canvas
        ref={canvas}
        className="hidden-canvas"
      />

      {/* Show the chosen photograph */}
      {imagePreview && (
        <div className="preview-box">
          <img
            src={imagePreview}
            alt="Selected meal"
          />

          <p>{imageName}</p>

          <button
            type="button"
            className="text-button"
            onClick={removeImage}
          >
            Remove and choose another
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
