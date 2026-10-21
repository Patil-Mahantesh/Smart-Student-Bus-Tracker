
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def _database_path():
    configured_path = os.getenv("DATABASE_PATH")

    if not configured_path:
        return BASE_DIR / "smart_student_bus_tracker.db"

    path = Path(configured_path)

    if path.is_absolute():
        return path

    return PROJECT_DIR / path


def _load_secret_key():
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key or not secret_key.strip():
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured in the environment"
        )

    return secret_key.strip()


def _load_environment():
    environment = os.getenv(
        "APP_ENV",
        "development"
    ).strip().lower()

    if environment not in {"development", "production"}:
        raise RuntimeError(
            "APP_ENV must be 'development' or 'production'"
        )

    return environment


class Config:
    ENV = _load_environment()
    SECRET_KEY = _load_secret_key()

    DATABASE_PATH = _database_path()

    CORS_ORIGINS = [
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5177"
        ).split(",")
        if origin.strip()
    ]

    MAP_TILE_URL = os.getenv(
        "MAP_TILE_URL",
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    )

    DEBUG = ENV == "development"


class DevelopmentConfig(Config):
    ENV = "development"


class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False


def get_config():
    if Config.ENV == "production":
        return ProductionConfig

    return DevelopmentConfig
