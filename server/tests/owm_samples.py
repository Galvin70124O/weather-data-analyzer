"""Sample OpenWeatherMap answers (same shape as the real API), for mocking with respx."""
from datetime import UTC, datetime

LONDON = {"name": "London", "lat": 51.5073219, "lon": -0.1276474, "country": "GB", "state": "England",
          "local_names": {"en": "London"}}
LONDON_ON = {"name": "London", "lat": 42.9832406, "lon": -81.243372, "country": "CA", "state": "Ontario"}


def geocode_answer() -> list[dict]:
    # The API sometimes returns the same place twice: the parser must drop the duplicate
    return [LONDON, LONDON_ON, dict(LONDON)]


def current_answer(dt: int = 1_761_134_400, temp: float = 14.2, condition_id: int = 500, icon: str = "10d",
                   timezone: int = 3600) -> dict:
    return {
        "coord": {"lon": -0.1276, "lat": 51.5073},
        "weather": [{"id": condition_id, "main": "Rain", "description": "light rain", "icon": icon}],
        "main": {"temp": temp, "feels_like": temp - 1.5, "temp_min": temp - 2, "temp_max": temp + 1,
                 "pressure": 1012, "humidity": 81},
        "visibility": 10000,
        "wind": {"speed": 4.6, "deg": 230, "gust": 8.2},
        "clouds": {"all": 75},
        "dt": dt,
        "sys": {"country": "GB", "sunrise": 1_761_115_000, "sunset": 1_761_152_000},
        "timezone": timezone,
        "name": "London",
        "cod": 200,
    }


def forecast_answer(start: datetime = datetime(2026, 10, 22, 12, tzinfo=UTC), steps: int = 40,
                    timezone: int = 3600) -> dict:
    entries = []
    for i in range(steps):
        dt = int(start.timestamp()) + i * 3 * 3600
        hour = datetime.fromtimestamp(dt, UTC).hour
        temp = 10 + (hour % 24) / 2          # warmer later in the day, repeats every day
        entries.append({
            "dt": dt,
            "main": {"temp": temp, "feels_like": temp - 1, "temp_min": temp - 0.5, "temp_max": temp + 0.5,
                     "pressure": 1010, "humidity": 70 + i % 10},
            "weather": [{"id": 500 if i % 4 == 0 else 803, "main": "Rain" if i % 4 == 0 else "Clouds",
                         "description": "light rain" if i % 4 == 0 else "broken clouds",
                         "icon": "10d" if 6 <= hour < 18 else "04n"}],
            "wind": {"speed": 3 + i % 5, "deg": 200},
            "pop": 0.6 if i % 4 == 0 else 0.1,
            **({"rain": {"3h": 1.2}} if i % 4 == 0 else {}),
            "dt_txt": datetime.fromtimestamp(dt, UTC).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return {"cod": "200", "cnt": steps, "list": entries,
            "city": {"name": "London", "country": "GB", "timezone": timezone, "sunrise": 1, "sunset": 2}}
