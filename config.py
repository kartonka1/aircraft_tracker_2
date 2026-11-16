"""Настройки проекта и перечень наблюдаемых стран."""

import os

from dotenv import load_dotenv

load_dotenv()

COUNTRIES = (
    ("de", "Germany"),
    ("nl", "Netherlands"),
    ("be", "Belgium"),
    ("lu", "Luxembourg"),
    ("ch", "Switzerland"),
    ("at", "Austria"),
    ("cz", "Czechia"),
    ("sk", "Slovakia"),
    ("hu", "Hungary"),
    ("pl", "Poland"),
)


def get_db_config() -> dict:
    """Возвращает параметры подключения к PostgreSQL из переменных окружения."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "airspace_tracker"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


def get_opensky_credentials() -> tuple[str | None, str | None]:
    """Возвращает необязательные OAuth2-учетные данные OpenSky."""
    return os.getenv("OPENSKY_CLIENT_ID"), os.getenv("OPENSKY_CLIENT_SECRET")


def get_nominatim_user_agent() -> str:
    """Возвращает идентификатор приложения для запросов к Nominatim."""
    return os.getenv("NOMINATIM_USER_AGENT", "AircraftStudyCoursework/1.0 (educational project)")
