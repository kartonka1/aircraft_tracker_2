"""Точка входа: получение стран, самолетов и вывод отчетов."""

import sys
import time

import psycopg2
import requests

from aircraft_service import AircraftService
from api_clients import NominatimClient, OpenSkyClient
from config import (
    COUNTRIES,
    get_db_config,
    get_nominatim_user_agent,
    get_opensky_credentials,
)
from database import AircraftRepository
from db_manager import DBManager


def ensure_countries(repository: AircraftRepository, client: NominatimClient) -> list[dict]:
    """Загружает недостающие страны однократно, остальные берет из PostgreSQL."""
    cached = {country["code"]: country for country in repository.get_countries()}
    for code, name in COUNTRIES:
        if code in cached:
            continue
        print(f"Получение границ: {name}")
        country = client.get_country(code, name)
        repository.save_country(country)
        # Публичный Nominatim разрешает не более одного запроса в секунду.
        time.sleep(1.1)
    countries_by_code = {country["code"]: country for country in repository.get_countries()}
    return [countries_by_code[code] for code, _ in COUNTRIES]


def collect_aircraft(countries: list[dict], client: OpenSkyClient) -> list[dict]:
    """Собирает текущие самолеты, исключая стоящие на земле и дубликаты."""
    service = AircraftService()
    unique_planes = {}
    for country in countries:
        print(f"Получение самолетов: {country['name']}")
        payload = client.get_states(country)
        planes = service.filter_airborne(country, payload)
        for plane in planes:
            unique_planes.setdefault(plane["icao24"], plane)
        print(f"  В границах страны: {len(planes)}")
    return list(unique_planes.values())


def print_report(manager: DBManager) -> None:
    """Показывает результаты всех пяти обязательных методов DBManager."""
    print("\nСамолеты по странам:")
    for row in manager.get_countries_and_aeroplanes_count():
        print(f"  {row['country_name']}: {row['aeroplanes_count']}")
    aeroplanes = manager.get_all_aeroplanes()
    print(f"\nВсего самолетов: {len(aeroplanes)}")
    for row in aeroplanes[:5]:
        print(f"  {row['icao24']}: {row['callsign']} ({row['airspace_country']})")
    average = manager.get_avg_speed()
    if average is not None:
        print(f"\nСредняя скорость: {average:.2f} м/с ({average * 3.6:.1f} км/ч)")
    else:
        print("\nСредняя скорость: нет данных")
    fast = manager.get_aeroplanes_with_higher_speed()
    print(f"Быстрее средней: {len(fast)}")
    matches = manager.get_aeroplanes_with_keyword("ACA")
    print(f"Позывной содержит ACA: {len(matches)}")


def main() -> None:
    """Создает схему, получает актуальный снимок и запускает SQL-отчеты."""
    repository = AircraftRepository(get_db_config())
    nominatim = NominatimClient(get_nominatim_user_agent())
    opensky = OpenSkyClient(*get_opensky_credentials())
    try:
        repository.create_tables()
        countries = ensure_countries(repository, nominatim)
        aeroplanes = collect_aircraft(countries, opensky)
        repository.replace_aeroplanes(aeroplanes)
        print_report(DBManager(get_db_config()))
    finally:
        nominatim.close()
        opensky.close()


if __name__ == "__main__":
    try:
        main()
    except (psycopg2.Error, requests.RequestException, ValueError, RuntimeError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)
