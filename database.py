"""
SQLite database helpers for users and saved weather history.

The database lives in the data folder so the app keeps working locally and on
Render. On Render, attach a persistent disk to keep this file between deploys.
"""

import os
import sqlite3
from contextlib import closing

import pandas as pd


PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(PROJECT_FOLDER, "data")
DATABASE_FILE = os.environ.get(
    "WEATHER_DATABASE_FILE",
    os.path.join(DATA_FOLDER, "weather_app.db"),
)


def get_connection():
    """Open a SQLite connection with rows that behave like dictionaries."""
    database_folder = os.path.dirname(DATABASE_FILE)
    if database_folder:
        os.makedirs(database_folder, exist_ok=True)
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the database tables if they do not already exist."""
    with closing(get_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date_time TEXT NOT NULL,
                city TEXT NOT NULL,
                temperature_celsius REAL NOT NULL,
                humidity INTEGER NOT NULL,
                pressure INTEGER NOT NULL,
                weather_description TEXT NOT NULL,
                wind_speed REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def create_user(username, email, password_hash):
    """
    Save a new user.

    Returns (True, message) on success and (False, message) when the username or
    email already exists.
    """
    normalized_username = username.strip()
    normalized_email = email.strip().lower()

    try:
        with closing(get_connection()) as connection:
            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE lower(username) = lower(?) OR lower(email) = lower(?)
                """,
                (normalized_username, normalized_email),
            ).fetchone()

            if existing_user is not None:
                return False, "That username or email is already registered."

            connection.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (normalized_username, normalized_email, password_hash),
            )
            connection.commit()
        return True, "Account created successfully. You can log in now."
    except sqlite3.IntegrityError:
        return False, "That username or email is already registered."


def get_user_by_login(identifier):
    """Find a user by username or email address."""
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            SELECT id, username, email, password_hash
            FROM users
            WHERE lower(username) = lower(?) OR lower(email) = lower(?)
            """,
            (identifier.strip(), identifier.strip()),
        )
        return cursor.fetchone()


def save_weather_record(user_id, weather_data):
    """Save one weather lookup for the logged-in user."""
    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT INTO weather_history (
                user_id,
                date_time,
                city,
                temperature_celsius,
                humidity,
                pressure,
                weather_description,
                wind_speed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                weather_data["date_time"],
                weather_data["city"],
                weather_data["temperature_celsius"],
                weather_data["humidity"],
                weather_data["pressure"],
                weather_data["weather_description"],
                weather_data["wind_speed"],
            ),
        )
        connection.commit()


def load_weather_history(user_id):
    """Load only the weather history owned by one user."""
    with closing(get_connection()) as connection:
        data = pd.read_sql_query(
            """
            SELECT
                id,
                date_time,
                city,
                temperature_celsius,
                humidity,
                pressure,
                weather_description,
                wind_speed
            FROM weather_history
            WHERE user_id = ?
            ORDER BY date_time DESC
            """,
            connection,
            params=(user_id,),
        )

    if not data.empty:
        data["date_time"] = pd.to_datetime(data["date_time"], errors="coerce")
        data = data.dropna(subset=["date_time"])

    return data


def load_all_weather_history():
    """Load all saved weather records for local command-line analysis."""
    with closing(get_connection()) as connection:
        data = pd.read_sql_query(
            """
            SELECT
                users.username,
                weather_history.date_time,
                weather_history.city,
                weather_history.temperature_celsius,
                weather_history.humidity,
                weather_history.pressure,
                weather_history.weather_description,
                weather_history.wind_speed
            FROM weather_history
            JOIN users ON users.id = weather_history.user_id
            ORDER BY weather_history.date_time DESC
            """,
            connection,
        )

    if not data.empty:
        data["date_time"] = pd.to_datetime(data["date_time"], errors="coerce")
        data = data.dropna(subset=["date_time"])

    return data


def load_saved_searches(user_id, limit=8):
    """Return recent unique cities searched by the logged-in user."""
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            SELECT city, MAX(date_time) AS last_searched
            FROM weather_history
            WHERE user_id = ?
            GROUP BY lower(city)
            ORDER BY last_searched DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return cursor.fetchall()
