# Мониторинг самолетов (OpenSky + Nominatim + PostgreSQL)

Учебный проект на Python. Получает границы 10 европейских стран через Nominatim,
запрашивает состояния воздушных судов через OpenSky, фильтрует наземные суда
и проверяет принадлежность географическим границам (Shapely). Сохраняет
**актуальный снимок**, а не полную историю полетов, в PostgreSQL.

## Модули

- `config.py` — настройки PostgreSQL, API и список стран.
- `api_clients.py` — два HTTP-клиента (`requests`), OAuth2 OpenSky.
- `aircraft_service.py` — фильтрация данных OpenSky по полигонам стран.
- `database.py` — создание таблиц и сохранение данных (`psycopg2`).
- `db_manager.py` — все пять обязательных SQL-методов.
- `main.py` — запуск получения данных и отчетов.
- `tests/` — тесты без внешних сервисов.

## Подготовка в Windows / PyCharm

1. Установите PostgreSQL и создайте базу `airspace_tracker` (например, через pgAdmin: Databases → Create → Database).
   Можно выполнить SQL под учетной записью PostgreSQL:
   ```sql
   CREATE DATABASE airspace_tracker;
   ```
2. Откройте папку в PyCharm, создайте виртуальное окружение Python 3.10+.
3. Установите зависимости в терминале PyCharm:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Скопируйте `.env.example` в `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
5. Отредактируйте `DB_PASSWORD` и остальные DB-параметры при необходимости.
   Замените email в `NOMINATIM_USER_AGENT` на настоящий контактный адрес;
   не публикуйте `.env` в GitHub.
6. **OpenSky**: анонимный доступ возможен с меньшими лимитами. Для OAuth2
   зарегистрируйте API-клиент на https://opensky-network.org/ и укажите
   `OPENSKY_CLIENT_ID` и `OPENSKY_CLIENT_SECRET` в `.env`.
7. Запустите:
   ```powershell
   python main.py
   ```
8. Запустите тесты:
   ```powershell
   python -m unittest discover -s tests -v
   ```

Создание таблиц происходит автоматически. При первом запуске Nominatim
вызывается для десяти стран с паузой более 1 секунды. После первого запуска
страны и геометрии кешируются в PostgreSQL — последующие запуски повторно
геокодировать их не будут.

## Схема базы данных

`countries(id, code, name, south, north, west, east, geometry)`

`aeroplanes(icao24, country_id, callsign, origin_country, latitude, longitude,
baro_altitude, velocity, last_contact, observed_at)`

`country_id` — внешний ключ на `countries.id`. `icao24` — уникальный адрес
транспондера. В таблице сохраняются только сведения из **последнего** запуска.
Если API не смог ответить, старый снимок сохраняется (запись не начинается).

## Методы DBManager

```python
from config import get_db_config
from db_manager import DBManager

manager = DBManager(get_db_config())
print(manager.get_countries_and_aeroplanes_count())
print(manager.get_all_aeroplanes())
print(manager.get_avg_speed())
print(manager.get_aeroplanes_with_higher_speed())
print(manager.get_aeroplanes_with_keyword("ACA"))
```

Показатель `velocity` и результат `get_avg_speed()` измеряются в **м/с**, как
в OpenSky; для км/ч умножьте на `3.6`. Поле `origin_country` определяет
страну регистрации транспондера, **не** страну пролета. Страна пролета
определяется геометрией полигона и хранится через `country_id`.

Важно: географические границы стран — это приближение к территориальному
воздушному пространству, а не официальные границы авиационных районов (FIR).
Данные OpenSky могут быть неполными; частота и полнота данных зависят от покрытия.
Запросы для 10 стран выполняются последовательно, поэтому время снимка
для разных стран может немного различаться.

## Источники и ограничения

- [OpenSky REST API](https://openskynetwork.github.io/opensky-api/rest.html) — состояния `/states/all`, квоты, OAuth2.
- [Nominatim Search API](https://nominatim.org/release-docs/latest/api/Search/) — координаты и `polygon_geojson`.
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) — максимум 1 запрос в секунду, обязательный User-Agent, локальное кеширование.
- Геоданные: © OpenStreetMap contributors, ODbL, https://www.openstreetmap.org/copyright

Нельзя запускать частое автоматическое геокодирование стран. Кеширование
геометрий уже реализовано в базе; для регулярного использования за пределами
учебного проекта изучите политику Nominatim и условия OpenSky.

## Проверка данных в PostgreSQL

После запуска программы можно проверить сохранённые данные
через pgAdmin 4.

Количество стран:

```sql
SELECT COUNT(*) FROM countries;
```

Количество самолётов:

```sql
SELECT COUNT(*) FROM aeroplanes;
```

Средняя скорость самолётов:

```sql
SELECT ROUND(AVG(velocity)::numeric, 2)
FROM aeroplanes;
```

Проверка работы всех модулей:

```powershell
python -m unittest discover -s tests -v
```

Все 8 модульных тестов успешно пройдены.