"""All models, imported here so Alembic and the app see the same tables."""
from app.models.login_attempt import LoginAttempt
from app.models.user import User

__all__ = ["LoginAttempt", "User"]
