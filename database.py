"""Схема БД и операции записи в PostgreSQL."""

from contextlib import closing
from datetime import datetime
from json import dumps

import psycopg2
from psycopg2.extras import Json, RealDictCursor, execute_values


SCHEMA = """
CREATE TABLE IF NOT EXISTS countries (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL UNIQUE,
    south DOUBLE PRECISION NOT NULL,
    north DOUBLE PRECISION NOT NULL,
    west DOUBLE PRECISION NOT NULL,
    east DOUBLE PRECISION NOT NULL,
    geometry JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS aeroplanes (
    icao24 VARCHAR(6) PRIMARY KEY,
    country_id INTEGER NOT NULL REFERENCES countries(id),
    callsign VARCHAR(16),
    origin_country VARCHAR(100),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    baro_altitude DOUBLE PRECISION,
    velocity DOUBLE PRECISION,
    last_contact TIMESTAMPTZ NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_aeroplanes_country_id ON aeroplanes(country_id);
"""


class AircraftRepository:
    """Отвечает за создание таблиц и сохранение стран и самолетов."""

    def __init__(self, db_config: dict):
        """Сохраняет параметры PostgreSQL для новых подключений."""
        self.db_config = db_config

    def create_tables(self) -> None:
        """Создает отсутствующие таблицы и индекс."""
        with closing(psycopg2.connect(**self.db_config)) as conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(SCHEMA)

    def get_countries(self) -> list[dict]:
        """Получает ранее сохраненные страны вместе с границами."""
        with closing(psycopg2.connect(**self.db_config)) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM countries ORDER BY name")
                return [dict(row) for row in cursor.fetchall()]

    def save_country(self, country: dict) -> None:
        """Сохраняет географические данные страны или обновляет существующие."""
        with closing(psycopg2.connect(**self.db_config)) as conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO countries
                            (code, name, south, north, west, east, geometry)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (code) DO UPDATE SET
                            name = EXCLUDED.name,
                            south = EXCLUDED.south,
                            north = EXCLUDED.north,
                            west = EXCLUDED.west,
                            east = EXCLUDED.east,
                            geometry = EXCLUDED.geometry
                        """,
                        (
                            country["code"], country["name"],
                            country["south"], country["north"],
                            country["west"], country["east"],
                            Json(country["geometry"]),
                        ),
                    )

    def replace_aeroplanes(self, aeroplanes: list[dict]) -> None:
        """Атомарно заменяет предыдущий снимок новыми данными о самолетах."""
        with closing(psycopg2.connect(**self.db_config)) as conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM aeroplanes")
                    if not aeroplanes:
                        return
                    rows = [
                        (
                            plane["icao24"], plane["country_id"],
                            plane["callsign"], plane["origin_country"],
                            plane["latitude"], plane["longitude"],
                            plane["baro_altitude"], plane["velocity"],
                            plane["last_contact"], plane["observed_at"],
                        )
                        for plane in aeroplanes
                    ]
                    execute_values(
                        cursor,
                        """
                        INSERT INTO aeroplanes (
                            icao24, country_id, callsign, origin_country,
                            latitude, longitude, baro_altitude, velocity,
                            last_contact, observed_at
                        ) VALUES %s
                        """,
                        rows,
                        page_size=500,
                    )
