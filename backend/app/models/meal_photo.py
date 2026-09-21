import threading

from ..config import settings
from ..logic.meal_band_rules import (
    calc_band_from_food_group,
    calc_band_from_reading,
    photo_reject_reason,
)


_heic_photos_allowed = False


# iPhones save photographs as HEIC so the app needs to be able to open them
def allow_heic_photos() -> None:
    global _heic_photos_allowed

    if _heic_photos_allowed:
        return

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()

    except ImportError:
        pass

    _heic_photos_allowed = True


class MealPhotoModels:
    def __init__(self):
        self.loaded_dish_model = None
        self.loaded_caption_model = None
        self.loaded_food_group_model = None

        self._loading_lock = threading.Lock()

    # No model is loaded until it is needed and then it stays in memory
    def load_dish_model(self):
        if self.loaded_dish_model is not None:
            return

        # The lock stops two check-ins from loading the same model at once
        with self._loading_lock:
            # Check again in case another check-in loaded the model while this one waited
            if self.loaded_dish_model is not None:
                return

            self.loaded_dish_model = self._create_dish_model()

    # SigLIP2 names one dish from the Food-101 set
    def _create_dish_model(self):
        from transformers import pipeline

        return pipeline(
            "image-classification",
            model=settings.dish_model,
            top_k=1,
        )

    def load_caption_model(self):
        if self.loaded_caption_model is not None:
            return

        with self._loading_lock:
            if self.loaded_caption_model is not None:
                return

            self.loaded_caption_model = self._create_caption_model()

    # BLIP Large describes what is on the plate
    def _create_caption_model(self):
        from transformers import pipeline

        return pipeline(
            "image-text-to-text",
            model=settings.caption_model,
        )

    def load_food_group_model(self):
        if self.loaded_food_group_model is not None:
            return

        with self._loading_lock:
            if self.loaded_food_group_model is not None:
                return

            self.loaded_food_group_model = self._create_food_group_model()

    # The Kaludi classifier names one of twelve everyday food groups
    def _create_food_group_model(self):
        from transformers import pipeline

        return pipeline(
            "image-classification",
            model=settings.food_group_model,
            top_k=1,
        )

    def read_photo(self, image_path: str) -> dict:
        from PIL import (
            Image,
            UnidentifiedImageError,
        )

        allow_heic_photos()

        # Open the photograph and turn it into a normal colour image
        try:
            with Image.open(
                image_path
            ) as uploaded_image:
                image = uploaded_image.convert(
                    "RGB"
                )

        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
        ) as error:
            raise ValueError(
                "The photograph could not be opened."
            ) from error

        self.load_dish_model()
        self.load_caption_model()
        self.load_food_group_model()

        # Three models read the same photograph
        dish_output = self.loaded_dish_model(image)

        food_group_output = self.loaded_food_group_model(image)

        caption_output = self.loaded_caption_model(
            image,
            text="A photo of",
            max_new_tokens=40,
        )

        if not dish_output:
            raise ValueError(
                "The food in this photograph could not be recognised."
            )

        top_dish = dish_output[0]
        dish_label = top_dish["label"].replace("_", " ").strip().lower()
        dish_confidence = round(float(top_dish["score"]), 4)

        caption = ""

        if caption_output:
            caption = (caption_output[0].get("generated_text") or "").strip()

        # Photographs without food are refused before anything is shown
        reject_reason = photo_reject_reason(caption)

        if reject_reason == "drink":
            raise ValueError(
                "That looks like a drink. Drinks are not scored because they say very little about what you eat so please take a photograph of your food instead."
            )

        if reject_reason:
            raise ValueError(
                "This photograph does not seem to show food. Please take or upload another one."
            )

        food_group_label = ""
        food_group_confidence = 0.0

        if food_group_output:
            food_group_label = str(food_group_output[0]["label"]).strip()
            food_group_confidence = round(
                float(food_group_output[0]["score"]), 4
            )

        # The caption starts with "A photo of" so that part is removed before it is shown
        if caption.lower().startswith("a photo of"):
            caption = caption[len("a photo of"):].strip()

        # All three readings are shown and the user taps the one that matches their meal
        food_readings = [
            {
                "source": "dish",
                "label": dish_label,
                "confidence": dish_confidence,
                "band": calc_band_from_reading(dish_label),
            },
            {
                "source": "food_group",
                "label": food_group_label.lower(),
                "confidence": food_group_confidence,
                "band": calc_band_from_food_group(food_group_label),
            },
            {
                "source": "caption",
                "label": caption,
                "confidence": 0.0,
                "band": calc_band_from_reading(caption),
            },
        ]

        # Leave out a reading when the model gave nothing
        food_readings = [
            reading for reading in food_readings if reading["label"]
        ]

        # Use the first reading with a band until the user picks one
        first_band_found = next(
            (reading["band"] for reading in food_readings if reading["band"]),
            "mixed",
        )

        return {
            "food_label": dish_label,
            "food_candidates": food_readings,
            "nutrition_category": first_band_found,
        }


# A copy of the models is shared by every check-in
meal_photo_models = MealPhotoModels()


def read_meal_photo(
    image_path: str,
) -> dict:
    return meal_photo_models.read_photo(image_path)
