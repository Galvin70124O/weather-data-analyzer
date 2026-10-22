"""The test database guard itself (see conftest.check_test_database_is_safe)."""
from tests.conftest import same_database


def test_same_database_ignores_driver_and_options():
    assert same_database("postgresql://u:p@host:5432/db?sslmode=require", "postgresql+psycopg://u:x@host:5432/db")


def test_different_branch_or_database_is_not_the_same():
    assert not same_database("postgresql://u@ep-dev.neon.tech/app", "postgresql://u@ep-test.neon.tech/app")
    assert not same_database("postgresql://u@localhost:5432/app", "postgresql://u@localhost:5432/app_test")
