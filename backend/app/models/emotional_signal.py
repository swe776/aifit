import threading

from ..config import settings


# The five emotional signals chosen from the literature review
EMOTIONAL_SIGNALS = [
    "burnout",
    "low motivation",
    "fatigue",
    "high motivation",
    "neutral",
]


# The model is shown combination D of the reworded labels because it read burnout much better
SIGNAL_WORDS_SHOWN_TO_MODEL = {
    "burnout": "burnt out",
    "low motivation": "unmotivated",
    "fatigue": "physically tired",
    "high motivation": "high motivation",
    "neutral": "neutral",
}

# Turn the reworded labels back into the original labels used everywhere else
SHOWN_WORD_TO_SIGNAL = {
    shown: original
    for original, shown in SIGNAL_WORDS_SHOWN_TO_MODEL.items()
}


class EmotionalSignalModel:
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
                "zero-shot-classification",
                model=settings.emotion_model,
            )

    def detect_signal(self, transcript: str) -> dict:
        # An empty transcript is read as neutral without using the model
        if not transcript.strip():
            return {
                "label": "neutral",
                "confidence": 1.0,
                "scores": {
                    label: 1.0 if label == "neutral" else 0.0
                    for label in EMOTIONAL_SIGNALS
                },
            }

        self.load_model()

        # Zero-shot classification asks how much the transcript matches each signal
        result = self.loaded_model(
            transcript,
            candidate_labels=list(
                SIGNAL_WORDS_SHOWN_TO_MODEL.values()
            ),
            hypothesis_template="This person is feeling {}.",
            multi_label=False,
        )

        # Keep the confidence score of every signal because the scoring uses all five
        scores = {
            SHOWN_WORD_TO_SIGNAL[shown]: round(float(score), 4)
            for shown, score in zip(
                result["labels"],
                result["scores"],
            )
        }

        # The signal with the highest confidence is the one detected
        return {
            "label": SHOWN_WORD_TO_SIGNAL[result["labels"][0]],
            "confidence": round(float(result["scores"][0]), 4),
            "scores": scores,
        }


# A copy of the model is shared by every check-in
emotional_signal_model = EmotionalSignalModel()


def detect_emotional_signal(transcript: str) -> dict:
    return emotional_signal_model.detect_signal(transcript)
