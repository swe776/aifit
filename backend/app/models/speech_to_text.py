import logging
import subprocess
import threading

from ..config import settings

logger = logging.getLogger(__name__)


# Recordings quieter than this are treated as silence
SILENCE_VOLUME_LIMIT = 0.005


class SpeechToTextModel:
    def __init__(self):
        self.loaded_model = None

        self._loading_lock = threading.Lock()

    # No model is loaded until it is needed and then it stays in memory
    def load_model(self):
        if self.loaded_model is not None:
            return

        # The lock stops two check-ins from loading the same model at once
        with self._loading_lock:
            # Check again in case another check-in loaded the model while this one waited
            if self.loaded_model is not None:
                return

            from transformers import pipeline

            self.loaded_model = pipeline(
                "automatic-speech-recognition",
                model=settings.speech_model,
            )

    def transcribe(self, audio_path: str) -> str:
        import numpy as np

        # Convert the recording into a plain waveform first
        audio = self.read_audio(audio_path)

        if audio.size == 0:
            return ""

        volume = float(
            np.sqrt(np.mean(np.square(audio)))
        )

        # A silent recording is not sent to the model
        if volume < SILENCE_VOLUME_LIMIT:
            return ""

        self.load_model()

        # Whisper Base turns the recording into English text
        result = self.loaded_model(
            {
                "raw": audio,
                "sampling_rate": 16000,
            },
            generate_kwargs={
                "language": "en",
                "task": "transcribe",
            },
        )

        transcript = (result.get("text") or "").strip()

        # An empty string tells the user nothing usable was heard
        if self.is_invalid_recording(transcript):
            return ""

        return transcript

    @staticmethod
    def read_audio(audio_path: str):
        import numpy as np

        # FFmpeg reads any audio type and turns it into 16 kHz mono audio for Whisper
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            audio_path,
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "pipe:1",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
            )

        # Audio cannot be read when FFmpeg is not installed
        except FileNotFoundError as error:
            raise ValueError(
                "Audio could not be read because FFmpeg is not installed. Install FFmpeg and make sure it is on your PATH."
            ) from error

        # Log the reason FFmpeg gave so the problem can be found later
        if result.returncode != 0:
            reason = (
                result.stderr.decode("utf-8", "replace").strip()
                or "ffmpeg gave no reason"
            )

            logger.warning(
                "ffmpeg could not read %s: %s",
                audio_path,
                reason[-400:],
            )

            raise ValueError("The recording could not be opened.")

        if not result.stdout:
            logger.warning(
                "ffmpeg read %s but produced no audio", audio_path
            )

            raise ValueError(
                "No sound was found in that recording. Please try again."
            )

        return np.frombuffer(
            result.stdout,
            dtype=np.float32,
        )

    @staticmethod
    def is_invalid_recording(transcript: str) -> bool:
        if not transcript:
            return True

        words = transcript.lower().split()

        # A long transcript that keeps repeating the same few words is not a real check-in
        if len(words) >= 10:
            unique_word_ratio = len(set(words)) / len(words)

            if unique_word_ratio < 0.2:
                return True

        return False


# A copy of the model is shared by every check-in
speech_to_text_model = SpeechToTextModel()


def transcribe_audio(audio_path: str) -> str:
    return speech_to_text_model.transcribe(audio_path)
