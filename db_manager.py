"""Пять обязательных SQL-запросов к базе данных проекта."""

from contextlib import closing

import psycopg2
from psycopg2.extras import RealDictCursor


AIRCRAFT_SELECT = """
    SELECT a.icao24, a.callsign, a.origin_country,
           c.name AS airspace_country,
           a.latitude, a.longitude, a.baro_altitude,
           a.velocity, a.last_contact, a.observed_at
    FROM aeroplanes AS a
    JOIN countries AS c ON c.id = a.country_id
"""


class DBManager:
    """Предоставляет методы чтения статистики и сведений о самолетах."""

    def __init__(self, db_config: dict):
        """Принимает параметры подключения PostgreSQL."""
        self.db_config = db_config

    def _fetch(self, query: str, params: tuple | None = None) -> list[dict]:
        """Выполняет параметризованный SELECT и возвращает список словарей."""
        with closing(psycopg2.connect(**self.db_config)) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

    def get_countries_and_aeroplanes_count(self) -> list[dict]:
        """Возвращает все страны и число самолетов над каждой страной (JOIN)."""
        return self._fetch(
            """
            SELECT c.name AS country_name, COUNT(a.icao24) AS aeroplanes_count
            FROM countries AS c
            LEFT JOIN aeroplanes AS a ON a.country_id = c.id
            GROUP BY c.id, c.name
            ORDER BY c.name
            """
        )

    def get_all_aeroplanes(self) -> list[dict]:
        """Возвращает все самолеты с данными и страной нахождения."""
        return self._fetch(AIRCRAFT_SELECT + " ORDER BY a.icao24")

    def get_avg_speed(self) -> float | None:
        """Возвращает среднюю скорость в м/с без учета NULL; None, если данных нет."""
        rows = self._fetch("SELECT AVG(velocity)::DOUBLE PRECISION AS avg_speed FROM aeroplanes")
        return rows[0]["avg_speed"]

    def get_aeroplanes_with_higher_speed(self) -> list[dict]:
        """Возвращает самолеты со скоростью выше средней по всей таблице."""
        return self._fetch(
            AIRCRAFT_SELECT
            + " WHERE a.velocity > (SELECT AVG(velocity) FROM aeroplanes)"
            + " ORDER BY a.velocity DESC"
        )

    def get_aeroplanes_with_keyword(self, keyword: str) -> list[dict]:
        """Ищет самолеты по подстроке позывного без учета регистра."""
        if not keyword or not keyword.strip():
            raise ValueError("Для поиска необходима непустая строка")
        return self._fetch(
            AIRCRAFT_SELECT
            + " WHERE POSITION(LOWER(%s) IN LOWER(COALESCE(a.callsign, ''))) > 0"
            + " ORDER BY a.callsign, a.icao24",
            (keyword.strip(),),
        )
