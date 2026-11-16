"""Тесты отбора самолетов без доступа к OpenSky."""

import unittest

from aircraft_service import AircraftService


class AircraftServiceTests(unittest.TestCase):
    """Проверяет фильтрацию координат, наземного статуса и позывного."""

    def test_selects_only_airborne_inside_country(self):
        """Из трех состояний выбирает только воздушное судно внутри полигона."""
        country = {
            "id": 1,
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
            },
        }
        base = ["ab1234", " ACA123 ", "Canada", None, 1750000000,
                5.0, 5.0, 1000.0, False, 200.0, 45.0,
                0.0, None, 1100.0, None, False, 0]
        out = base.copy()
        out[5] = 12.0
        grounded = base.copy()
        grounded[8] = True
        payload = {"time": 1750000000, "states": [base, out, grounded]}
        result = AircraftService().filter_airborne(country, payload)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["callsign"], "ACA123")
        self.assertEqual(result[0]["velocity"], 200.0)
        self.assertEqual(result[0]["country_id"], 1)

    def test_empty_states(self):
        """Пустой ответ возвращает пустой список."""
        country = {
            "id": 1,
            "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]},
        }
        self.assertEqual(AircraftService().filter_airborne(
            country, {"time": 1750000000, "states": None}
        ), [])


if __name__ == "__main__":
    unittest.main()
