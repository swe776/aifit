# Unit tests for the speech, emotion and meal models using test replacements
import pytest
from PIL import Image

from backend.app.logic.meal_band_rules import (
    calc_b3p2_band,
    photo_reject_reason,
    calc_band_from_reading,
)
from backend.app.models.emotional_signal import (
    EMOTIONAL_SIGNALS,
    EmotionalSignalModel,
)
from backend.app.models.meal_photo import (
    MealPhotoModels,
)
from backend.app.models.speech_to_text import (
    SpeechToTextModel,
)


# A small plain image to stand in for a meal photograph
def create_test_image(tmp_path):
    image_path = tmp_path / "meal.jpg"

    Image.new(
        "RGB",
        (20, 20),
        color="white",
    ).save(image_path)

    return image_path


# Meal models that give set answers so the reading rules can be tested
def create_meal_photo_models(
    food_output,
    caption,
):
    model = MealPhotoModels()

    def fake_dish_model(
        *args,
        **kwargs,
    ):
        return food_output

    def fake_caption_model(
        *args,
        **kwargs,
    ):
        if caption is None:
            return []

        return [
            {
                "generated_text": caption
            }
        ]

    model.loaded_dish_model = fake_dish_model
    model.loaded_caption_model = (
        fake_caption_model
    )
    model.loaded_food_group_model = lambda *args, **kwargs: [
        {"label": "Vegetable", "score": 0.80}
    ]

    return model


@pytest.mark.parametrize(
    "food_label,expected_band",
    [
        ("grilled salmon", "mixed"),
        ("greek salad", "mixed"),
        ("tuna tartare", "mixed"),
        ("sushi", "mixed"),
        ("apple pie", "poor"),
        ("french fries", "poor"),
        ("chocolate cake", "poor"),
        ("ice cream", "poor"),
        ("pizza", "poor"),
        ("hamburger", "poor"),
        ("ramen", "mixed"),
    ],
)
def test_food_label_categories(
    food_label,
    expected_band,
):
    assert calc_band_from_reading(
        food_label
    ) == expected_band


@pytest.mark.parametrize(
    "meal_groups,expected_band",
    [
        (
            {"protein", "fibre", "produce", "wholegrain"},
            "balanced",
        ),
        (
            {"protein", "fibre", "produce"},
            "balanced",
        ),
        (
            {"protein", "satfat"},
            "mixed",
        ),
        (
            {"satfat"},
            "poor",
        ),
        (
            {"protein", "satfat", "sodium"},
            "poor",
        ),
    ],
)
def test_three_positive_two_poor_grouping_rule(
    meal_groups,
    expected_band,
):

    assert calc_b3p2_band(meal_groups) == expected_band


@pytest.mark.parametrize(
    "food_label,expected_band",
    [
        ("salmon with broccoli and brown rice", "balanced"),
        ("edamame", "mixed"),
        ("french fries", "poor"),
        ("chocolate cake", "poor"),
        ("borscht", None),
        ("pierogi", None),
        ("kimchi", None),
    ],
)
def test_a_dish_the_rules_do_not_know_has_no_band_to_show(
    food_label,
    expected_band,
):
    assert calc_band_from_reading(
        food_label
    ) == expected_band


def test_an_empty_reading_has_no_band():
    assert calc_band_from_reading("") is None
    assert calc_band_from_reading(None) is None


@pytest.mark.parametrize(
    "caption,expected_band",
    [
        (
            "a plate of salmon and vegetables",
            "balanced",
        ),
        (
            "chicken with vegetables",
            "balanced",
        ),
        (
            "a green salad with avocado",
            "mixed",
        ),
        (
            "a slice of chocolate cake",
            "poor",
        ),
        (
            "a plate of french fries",
            "poor",
        ),
        (
            "a bowl of ice cream",
            "poor",
        ),
        (
            "a hamburger on a plate",
            "poor",
        ),
        (
            "chicken served with rice",
            "mixed",
        ),
        (
            "pizza served with salad",
            "poor",
        ),
        (
            "a bowl on a table",
            None,
        ),
        (
            "a green field covered in grass",
            None,
        ),
    ],
)
def test_caption_categories(
    caption,
    expected_band,
):
    assert calc_band_from_reading(
        caption
    ) == expected_band


@pytest.mark.parametrize(
    "caption,expected_result",
    [
        ("a photograph of a hamburger", True),
        ("a bowl of food", True),
        ("breakfast on a plate", True),
        ("a fresh salad", True),
        ("a green field covered in grass", False),
        ("a red car on the road", False),
        ("", False),
    ],
)
def test_food_caption_check(
    caption,
    expected_result,
):
    assert (photo_reject_reason(caption) == "") is expected_result


def test_empty_emotion_input_is_neutral():
    model = EmotionalSignalModel()

    result = model.detect_signal("")

    assert result["label"] == "neutral"
    assert result["confidence"] == 1.0
    assert result["scores"]["neutral"] == 1.0


def test_emotion_model_output():
    model = EmotionalSignalModel()

    def fake_model(
        *args,
        **kwargs,
    ):
        return {
            "labels": [
                "physically tired",
                "neutral",
                "burnt out",
                "unmotivated",
                "high motivation",
            ],
            "scores": [
                0.70,
                0.10,
                0.08,
                0.07,
                0.05,
            ],
        }

    model.loaded_model = fake_model

    result = model.detect_signal(
        "I feel tired after every workout."
    )

    assert result["label"] == "fatigue"
    assert result["confidence"] == 0.70
    assert result["scores"]["fatigue"] == 0.70
    assert result["scores"]["burnout"] == 0.08
    assert set(result["scores"]) == set(EMOTIONAL_SIGNALS)


def test_every_label_has_wording_and_maps_back():
    from backend.app.models.emotional_signal import (
        SHOWN_WORD_TO_SIGNAL,
        SIGNAL_WORDS_SHOWN_TO_MODEL,
    )

    assert set(SIGNAL_WORDS_SHOWN_TO_MODEL) == set(EMOTIONAL_SIGNALS)

    shown = list(SIGNAL_WORDS_SHOWN_TO_MODEL.values())
    assert len(shown) == len(set(shown))

    for label in EMOTIONAL_SIGNALS:
        assert (
            SHOWN_WORD_TO_SIGNAL[
                SIGNAL_WORDS_SHOWN_TO_MODEL[label]
            ]
            == label
        )


def test_the_wording_reads_as_a_sentence():
    from backend.app.models.emotional_signal import (
        SIGNAL_WORDS_SHOWN_TO_MODEL,
    )

    assert (
        SIGNAL_WORDS_SHOWN_TO_MODEL["burnout"] == "burnt out"
    )
    assert (
        SIGNAL_WORDS_SHOWN_TO_MODEL["fatigue"]
        == "physically tired"
    )


def test_meal_photo_models_output(tmp_path):
    image_path = create_test_image(
        tmp_path
    )

    model = create_meal_photo_models(
        [
            {
                "label": "grilled_salmon",
                "score": 0.88,
            },
            {
                "label": "sushi",
                "score": 0.08,
            },
            {
                "label": "pizza",
                "score": 0.04,
            },
        ],
        "a plate of salmon and vegetables",
    )

    result = model.read_photo(
        str(image_path)
    )

    readings = {
        reading["source"]: reading
        for reading in result["food_candidates"]
    }

    assert result["food_label"] == "grilled salmon"
    assert readings["dish"]["confidence"] == 0.88
    assert readings["dish"]["band"] == "mixed"
    assert readings["caption"]["band"] == "balanced"

    assert result["nutrition_category"] == "mixed"


def test_caption_and_dish_readings_are_separate(
    tmp_path,
):
    image_path = create_test_image(
        tmp_path
    )

    dishes = [
        {
            "label": "grilled_salmon",
            "score": 0.90,
        },
    ]

    disagreeing = create_meal_photo_models(
        dishes,
        "a slice of chocolate cake",
    ).read_photo(str(image_path))

    agreeing = create_meal_photo_models(
        dishes,
        "a plate of salmon and vegetables",
    ).read_photo(str(image_path))

    def band_of(result, source):
        return next(
            reading["band"]
            for reading in result["food_candidates"]
            if reading["source"] == source
        )

    assert band_of(disagreeing, "caption") == "poor"
    assert band_of(agreeing, "caption") == "balanced"

    assert band_of(disagreeing, "dish") == (
        band_of(agreeing, "dish")
    )
    assert disagreeing["nutrition_category"] == (
        agreeing["nutrition_category"]
    )


def test_a_caption_with_no_band_leaves_the_other_readings_to_decide(
    tmp_path,
):
    image_path = create_test_image(
        tmp_path
    )

    model = create_meal_photo_models(
        [
            {
                "label": "grilled_salmon",
                "score": 0.90,
            },
        ],
        "a bowl on a table",
    )

    result = model.read_photo(
        str(image_path)
    )

    caption_reading = next(
        reading
        for reading in result["food_candidates"]
        if reading["source"] == "caption"
    )

    assert caption_reading["band"] is None
    assert result["nutrition_category"] in (
        "balanced",
        "mixed",
        "poor",
    )


def test_non_food_image_is_rejected(
    tmp_path,
):
    image_path = create_test_image(
        tmp_path
    )

    model = create_meal_photo_models(
        [
            {
                "label": "pizza",
                "score": 0.60,
            },
        ],
        "a green field covered in grass",
    )

    with pytest.raises(
        ValueError,
        match="does not seem to show food",
    ):
        model.read_photo(
            str(image_path)
        )


def test_a_drink_on_its_own_is_refused_as_a_drink(
    tmp_path,
):
    image_path = create_test_image(
        tmp_path
    )

    model = create_meal_photo_models(
        [
            {
                "label": "espresso",
                "score": 0.70,
            },
        ],
        "a cup of tea on a table",
    )

    with pytest.raises(
        ValueError,
        match="That looks like a drink",
    ):
        model.read_photo(
            str(image_path)
        )


def test_empty_food_output_is_rejected(
    tmp_path,
):
    image_path = create_test_image(
        tmp_path
    )

    model = create_meal_photo_models(
        [],
        "a plate of food",
    )

    with pytest.raises(
        ValueError,
        match="could not be recognised",
    ):
        model.read_photo(
            str(image_path)
        )


def test_corrupted_image_is_rejected(
    tmp_path,
):
    image_path = tmp_path / "broken.jpg"

    image_path.write_bytes(
        b"this is not an image"
    )

    model = MealPhotoModels()

    with pytest.raises(
        ValueError,
        match="photograph could not be opened",
    ):
        model.read_photo(
            str(image_path)
        )


@pytest.mark.parametrize(
    "transcript",
    [
        "",
        "hello " * 12,
        "test " * 20,
    ],
)
def test_invalid_transcript_is_rejected(
    transcript,
):
    assert SpeechToTextModel.is_invalid_recording(
        transcript
    ) is True


@pytest.mark.parametrize(
    "transcript",
    [
        "hello world",
        "I feel tired after every workout.",
        (
            "I trained three times this week and feel okay."
        ),
    ],
)
def test_valid_transcript_is_accepted(
    transcript,
):
    assert SpeechToTextModel.is_invalid_recording(
        transcript
    ) is False


def test_every_food101_dish_is_accepted_as_food():
    from backend.app.logic.meal_band_rules import FOOD101_DISH_NAMES

    assert len(FOOD101_DISH_NAMES) == 101

    for dish in FOOD101_DISH_NAMES:
        assert photo_reject_reason(f"a photo of {dish}") == ""


def test_a_food_the_table_cannot_place_shows_as_not_sure():
    from backend.app.logic.meal_band_rules import (
        calc_band_from_reading,
        photo_reject_reason,
    )

    for caption in ("a plate of pierogi", "a bowl of borscht"):
        assert photo_reject_reason(caption) == ""
        assert calc_band_from_reading(caption) is None


# A second of silence
def _silent_audio(_path):
    import numpy as np

    return np.zeros(16000, dtype=np.float32)


# A second of loud sound
def _loud_audio(_path):
    import numpy as np

    return np.full(16000, 0.5, dtype=np.float32)


def test_silent_audio_is_rejected_without_loading_whisper(monkeypatch):
    from backend.app.models.speech_to_text import SpeechToTextModel

    speech = SpeechToTextModel()
    monkeypatch.setattr(
        SpeechToTextModel, "read_audio", staticmethod(_silent_audio)
    )

    def fail_if_loaded():
        raise AssertionError(
            "Whisper must not be loaded for silent audio."
        )

    monkeypatch.setattr(speech, "load_model", fail_if_loaded)

    assert speech.transcribe("anything.wav") == ""


def test_empty_audio_is_rejected(monkeypatch):
    import numpy as np

    from backend.app.models.speech_to_text import SpeechToTextModel

    speech = SpeechToTextModel()
    monkeypatch.setattr(
        SpeechToTextModel,
        "read_audio",
        staticmethod(
            lambda _path: np.array([], dtype=np.float32)
        ),
    )

    assert speech.transcribe("anything.wav") == ""


def test_repetitive_transcript_is_rejected(monkeypatch):
    from backend.app.models.speech_to_text import SpeechToTextModel

    speech = SpeechToTextModel()
    monkeypatch.setattr(
        SpeechToTextModel, "read_audio", staticmethod(_loud_audio)
    )
    monkeypatch.setattr(speech, "load_model", lambda: None)
    speech.loaded_model = lambda *args, **kwargs: {
        "text": "thank you " * 12
    }

    assert speech.transcribe("anything.wav") == ""


def test_usable_transcript_is_returned(monkeypatch):
    from backend.app.models.speech_to_text import SpeechToTextModel

    speech = SpeechToTextModel()
    monkeypatch.setattr(
        SpeechToTextModel, "read_audio", staticmethod(_loud_audio)
    )
    monkeypatch.setattr(speech, "load_model", lambda: None)
    speech.loaded_model = lambda *args, **kwargs: {
        "text": "  I felt tired after training today.  "
    }

    assert speech.transcribe("anything.wav") == "I felt tired after training today."


def test_missing_ffmpeg_is_reported(monkeypatch):
    import subprocess

    from backend.app.models.speech_to_text import SpeechToTextModel

    def no_ffmpeg(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "run", no_ffmpeg)

    with pytest.raises(ValueError, match="FFmpeg is not installed"):
        SpeechToTextModel.read_audio("anything.wav")


def test_audio_with_no_sound_raises(monkeypatch):
    import subprocess

    from backend.app.models.speech_to_text import SpeechToTextModel

    class EmptyResult:
        returncode = 0
        stdout = b""
        stderr = b""

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: EmptyResult(),
    )

    with pytest.raises(ValueError, match="No sound was found"):
        SpeechToTextModel.read_audio("anything.wav")


def test_unreadable_audio_raises(monkeypatch):
    import subprocess

    from backend.app.models.speech_to_text import SpeechToTextModel

    class FailingModel:
        returncode = 1
        stdout = b""
        stderr = b"bad file"

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: FailingModel(),
    )

    with pytest.raises(ValueError):
        SpeechToTextModel.read_audio("broken.wav")


def test_a_plural_ending_in_ies_still_counts_as_food():
    from backend.app.logic.meal_band_rules import photo_reject_reason

    assert photo_reject_reason("a photo of berries") == ""
    assert photo_reject_reason("two curries") == ""


@pytest.mark.parametrize(
    "caption",
    [
        "a cup of black coffee on a table",
        "a glass of water",
        "a cup of tea",
        "a bottle of juice",
        "a can of soda",
    ],
)
def test_a_photograph_of_only_a_drink_is_not_a_meal(caption):
    from backend.app.logic.meal_band_rules import photo_reject_reason

    assert photo_reject_reason(caption) == "drink"


@pytest.mark.parametrize(
    "caption",
    [
        "a plate of rice and eggs with a glass of water",
        "a burger and fries with a cola",
        "a bowl of noodles and a cup of tea",
        "a single red apple",
        "a plate of chicken with rice",
    ],
)
def test_a_meal_is_still_accepted_when_a_drink_is_beside_it(caption):
    from backend.app.logic.meal_band_rules import photo_reject_reason

    assert photo_reject_reason(caption) == ""
