"""
Test setup: a real PostgreSQL test database (your Neon test branch, or the CI service container).

Safety: the tests WIPE every table before each test, so they refuse to run unless
TEST_DATABASE_URL is set and is different from DATABASE_URL.
"""
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

SERVER_DIR = Path(__file__).resolve().parents[1]


def same_database(url_a: str, url_b: str) -> bool:
    """True if two URLs point at the same database (ignores driver name and options like sslmode)."""
    a, b = make_url(url_a), make_url(url_b)
    return (a.host, a.port, a.database, a.username) == (b.host, b.port, b.database, b.username)


def check_test_database_is_safe() -> str:
    settings = get_settings()
    if not settings.test_database_url:
        pytest.exit("TEST_DATABASE_URL is not set. Point it at a separate test database (it gets wiped).", returncode=2)
    if same_database(settings.test_database_url, settings.database_url):
        pytest.exit("TEST_DATABASE_URL is the same database as DATABASE_URL. Refusing to wipe it.", returncode=2)
    return settings.test_database_url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = check_test_database_is_safe()
    # Build the schema exactly like production does: with the Alembic migrations
    config = Config(str(SERVER_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(SERVER_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
    return url


@pytest.fixture(scope="session")
def session_factory(test_database_url: str) -> Iterator[sessionmaker[Session]]:
    engine = create_engine(test_database_url)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(session_factory: sessionmaker[Session]) -> Iterator[None]:
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with session_factory() as db:
        db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        db.commit()
    yield


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def app(session_factory: sessionmaker[Session]):
    application = create_app()

    def test_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = test_db
    return application


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def make_client(app):
    """Several independent browsers (each with its own cookie jar)."""
    return lambda: TestClient(app)


def register(client: TestClient, username: str = "alice", email: str | None = None, password: str = "correct horse 1"):
    return client.post("/api/auth/register",
                       json={"username": username, "email": email or f"{username}@example.com", "password": password})
