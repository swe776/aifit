from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# These are the project settings and the secret key is read from the .env file
class Settings(BaseSettings):
    app_name: str = "AI.FIT"
    secret_key: str
    database_url: str = "sqlite:///./aifit.db"
    # A login lasts for one hour
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # The final models selected through the model evaluation in Chapter 5
    speech_model: str = "openai/whisper-base"
    emotion_model: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    dish_model: str = "prithivMLmods/Food-101-93M"
    caption_model: str = "Salesforce/blip-image-captioning-large"

    food_group_model: str = "Kaludi/food-category-classification-v2.0"

    # Audio is limited to 25 MB and images to 15 MB
    max_audio_mb: int = 25
    max_image_mb: int = 15

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


# Only known audio file types are accepted
ALLOWED_AUDIO_FILE_TYPES = {
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".ogg",
    ".oga",
    ".webm",
}

# HEIC is accepted because iPhones save photographs as HEIC and users used IPhones for testing
ALLOWED_IMAGE_FILE_TYPES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
}
