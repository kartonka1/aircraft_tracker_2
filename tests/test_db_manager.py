"""Изолированные проверки SQL-методов без подключения к PostgreSQL."""

import unittest
from unittest.mock import patch

from db_manager import DBManager


class DBManagerTests(unittest.TestCase):
    """Проверяет вызовы методов и безопасную передачу параметров поиска."""

    def setUp(self):
        """Создает экземпляр менеджера с тестовой конфигурацией."""
        self.manager = DBManager({})

    def test_countries_count_uses_left_join(self):
        """Число судов учитывает страны без самолетов."""
        with patch.object(self.manager, "_fetch", return_value=[]) as fetch:
            self.manager.get_countries_and_aeroplanes_count()
            self.assertIn("LEFT JOIN", fetch.call_args.args[0])

    def test_all_aeroplanes_uses_join(self):
        """Все самолеты выводятся со страной нахождения."""
        with patch.object(self.manager, "_fetch", return_value=[]) as fetch:
            self.manager.get_all_aeroplanes()
            self.assertIn("JOIN countries", fetch.call_args.args[0])

    def test_avg_uses_sql_avg(self):
        """Средняя скорость вычисляется SQL-функцией AVG."""
        with patch.object(self.manager, "_fetch", return_value=[{"avg_speed": 210.0}]):
            self.assertEqual(self.manager.get_avg_speed(), 210.0)

    def test_higher_speed_uses_subquery(self):
        """Список быстрых судов выбирается подзапросом AVG."""
        with patch.object(self.manager, "_fetch", return_value=[]) as fetch:
            self.manager.get_aeroplanes_with_higher_speed()
            self.assertIn("a.velocity > (SELECT AVG(velocity)", fetch.call_args.args[0])

    def test_keyword_is_parameterized(self):
        """Искомая строка передается отдельно от текста SQL."""
        with patch.object(self.manager, "_fetch", return_value=[]) as fetch:
            self.manager.get_aeroplanes_with_keyword("ACA")
            self.assertEqual(fetch.call_args.args[1], ("ACA",))

    def test_empty_keyword_rejected(self):
        """Пустая поисковая строка вызывает ошибку."""
        with self.assertRaises(ValueError):
            self.manager.get_aeroplanes_with_keyword(" ")


if __name__ == "__main__":
    unittest.main()
