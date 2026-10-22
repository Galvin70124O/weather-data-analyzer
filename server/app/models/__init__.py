"""All models, imported here so Alembic and the app see the same tables."""
from app.models.api_cache import ApiCache
from app.models.city import City
from app.models.history import ClimateNormal, DailyWeather
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.models.user_city import FavoriteCity, RecentSearch, WeatherSnapshot

__all__ = ["ApiCache", "City", "ClimateNormal", "DailyWeather", "FavoriteCity", "LoginAttempt", "RecentSearch", "User",
           "WeatherSnapshot"]
