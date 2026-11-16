"""Отбор самолетов, находящихся над выбранной страной."""

from datetime import datetime, timezone

from shapely.geometry import Point, shape


class AircraftService:
    """Преобразует данные OpenSky и проверяет принадлежность к геометрии страны."""

    def filter_airborne(self, country: dict, payload: dict) -> list[dict]:
        """Возвращает только находящиеся в воздухе суда в границах страны."""
        polygon = shape(country["geometry"])
        observed_at = datetime.fromtimestamp(payload["time"], tz=timezone.utc)
        result = []
        for state in payload.get("states") or []:
            if len(state) < 17 or state[8] is not False:
                continue
            icao24, longitude, latitude = state[0], state[5], state[6]
            if not icao24 or longitude is None or latitude is None:
                continue
            if not polygon.covers(Point(longitude, latitude)):
                continue
            if state[4] is None:
                continue
            result.append(
                {
                    "icao24": str(icao24).lower(),
                    "country_id": country["id"],
                    "callsign": state[1].strip() or None if state[1] else None,
                    "origin_country": state[2],
                    "longitude": longitude,
                    "latitude": latitude,
                    "baro_altitude": state[7],
                    "velocity": state[9],
                    "last_contact": datetime.fromtimestamp(state[4], tz=timezone.utc),
                    "observed_at": observed_at,
                }
            )
        return result
