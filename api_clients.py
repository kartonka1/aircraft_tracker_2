"""Клиенты для Nominatim и OpenSky Network."""

import time

import requests


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPENSKY_URL = "https://opensky-network.org/api/states/all"
TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/"
    "protocol/openid-connect/token"
)


class NominatimClient:
    """Получает границы стран через публичный API Nominatim."""

    def __init__(self, user_agent: str):
        """Создает HTTP-сессию с идентификатором учебного приложения."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def get_country(self, code: str, name: str) -> dict:
        """Возвращает границы, название и геометрию одной страны."""
        response = self.session.get(
            NOMINATIM_URL,
            params={
                "q": name,
                "countrycodes": code,
                "featuretype": "country",
                "format": "jsonv2",
                "limit": 1,
                "polygon_geojson": 1,
            },
            timeout=(10, 60),
        )
        response.raise_for_status()
        results = response.json()
        if not results or "geojson" not in results[0]:
            raise ValueError(f"Nominatim не вернул границы страны: {name}")

        item = results[0]
        south, north, west, east = map(float, item["boundingbox"])
        return {
            "code": code,
            "name": name,
            "south": south,
            "north": north,
            "west": west,
            "east": east,
            "geometry": item["geojson"],
        }

    def close(self) -> None:
        """Закрывает HTTP-сессию."""
        self.session.close()


class OpenSkyClient:
    """Читает актуальные данные о воздушных судах через OpenSky."""

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        """Настраивает анонимный доступ либо OAuth2 с кешированием токена."""
        if bool(client_id) != bool(client_secret):
            raise ValueError("Нужно указать оба параметра OPENSKY_CLIENT_ID и OPENSKY_CLIENT_SECRET")
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self._token = None
        self._expires_at = 0.0

    def _get_token(self) -> str | None:
        """Получает или переиспользует еще действующий OAuth2-токен."""
        if not self.client_id:
            return None
        if self._token and time.monotonic() < self._expires_at:
            return self._token

        response = self.session.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        token_data = response.json()
        self._token = token_data["access_token"]
        lifetime = int(token_data.get("expires_in", 1800))
        self._expires_at = time.monotonic() + max(0, lifetime - 60)
        return self._token

    def get_states(self, country: dict) -> dict:
        """Запрашивает текущие состояния в ограничивающем прямоугольнике страны."""
        params = {
            "lamin": country["south"],
            "lamax": country["north"],
            "lomin": country["west"],
            "lomax": country["east"],
        }
        for attempt in range(2):
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = self.session.get(
                OPENSKY_URL, params=params, headers=headers, timeout=(10, 60)
            )
            if response.status_code == 401 and token and attempt == 0:
                self._token = None
                continue
            if response.status_code == 429:
                retry = response.headers.get("X-Rate-Limit-Retry-After-Seconds", "неизвестно")
                raise RuntimeError(
                    f"OpenSky: лимит запросов исчерпан (HTTP 429). "
                    f"Повторить через {retry} сек."
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or "time" not in payload:
                raise ValueError("OpenSky вернул некорректный ответ")
            return payload
        raise RuntimeError("Не удалось обновить токен OpenSky")

    def close(self) -> None:
        """Закрывает HTTP-сессию."""
        self.session.close()
