-- Runs once when the docker-compose Postgres volume is first created: a separate test database.
CREATE DATABASE weather_test OWNER weather;
