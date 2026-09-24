import os
import secrets
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
    return path if path.is_absolute() else PROJECT_DIR / path


class Config:
    ENV = os.getenv("APP_ENV", "development").lower()
    SECRET_KEY = os.getenv("JWT_SECRET_KEY") or (
        secrets.token_urlsafe(32) if ENV != "production" else None
    )
    DATABASE_PATH = _database_path()
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5177"
        ).split(",")
        if origin.strip()
    ]
    MAP_TILE_URL = os.getenv(
        "MAP_TILE_URL",
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    )
    DEBUG = ENV == "development"


class DevelopmentConfig(Config):
    ENV = "development"


class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False


def get_config():
    config_class = ProductionConfig if Config.ENV == "production" else DevelopmentConfig
    if config_class.ENV == "production" and not config_class.SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY must be set in production")
    return config_class