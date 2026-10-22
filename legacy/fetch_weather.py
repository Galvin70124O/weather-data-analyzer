"""
Fetch live weather data from OpenWeatherMap and save it to a CSV file.
"""

import csv
import os
from datetime import datetime

import requests
from dotenv import load_dotenv


# Load local secrets from .env during development. Render environment variables
# are already available through os.getenv, so this stays deployment-friendly.
load_dotenv()

# OpenWeatherMap API key. Set this in .env locally or as an environment
# variable on Render. Never hardcode real API keys in source code.
API_KEY = os.getenv("OPENWEATHER_API_KEY")

# API URL for current weather data.
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Store all weather records in this CSV file.
# The path starts from this file's folder, so it works even if the app is
# launched from another directory.
PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(PROJECT_FOLDER, "data")
CSV_FILE = os.path.join(DATA_FOLDER, "weather.csv")

# This variable stores the latest error message. The Streamlit app can read it
# and show a friendly message on the web page.
LAST_ERROR = ""

# These are the columns used everywhere in the project.
CSV_COLUMNS = [
    "date_time",
    "city",
    "temperature_celsius",
    "humidity",
    "pressure",
    "weather_description",
    "wind_speed",
]


def set_last_error(message):
    """Save and print the latest error message."""
    global LAST_ERROR
    LAST_ERROR = message
    print(message)


def get_last_error():
    """Return the latest error message for Streamlit or other modules."""
    return LAST_ERROR


def create_csv_if_missing():
    """Create the data folder and CSV file if they do not already exist."""
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
    except OSError as error:
        set_last_error(f"Could not create the data folder: {error}")
        return False

    if not os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)

                # These column names make the CSV easy to read with pandas later.
                writer.writerow(CSV_COLUMNS)
        except OSError as error:
            set_last_error(f"Could not create the CSV file: {error}")
            return False

    return True


def fetch_weather_data(city):
    """
    Fetch live weather details for one city.

    Returns a dictionary when successful, or None when something goes wrong.
    """
    try:
        global LAST_ERROR
        LAST_ERROR = ""

        if not API_KEY:
            set_last_error(
                "OpenWeatherMap API key is missing. Set OPENWEATHER_API_KEY in "
                "your .env file locally or in Render environment variables."
            )
            return None

        parameters = {
            "q": city,
            "appid": API_KEY,
            # Metric units make OpenWeatherMap return temperature in Celsius.
            "units": "metric",
        }

        response = requests.get(BASE_URL, params=parameters, timeout=10)

        # Raise an error for bad responses such as 404 or 401.
        response.raise_for_status()

        data = response.json()

        weather_data = {
            "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "city": data["name"],
            "temperature_celsius": round(data["main"]["temp"], 2),
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather_description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
        }

        return weather_data

    except requests.exceptions.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            set_last_error("City not found. Please check the city name and try again.")
        elif error.response is not None and error.response.status_code == 401:
            set_last_error("Invalid API key. Please check the OpenWeatherMap API key.")
        else:
            set_last_error("Could not fetch weather data. Please try again later.")
    except requests.exceptions.ConnectionError:
        set_last_error("Network error. Please check your internet connection.")
    except requests.exceptions.Timeout:
        set_last_error("The request timed out. Please try again.")
    except requests.exceptions.RequestException as error:
        set_last_error(f"An API request error occurred: {error}")
    except KeyError:
        set_last_error("Weather data was received, but some expected fields were missing.")

    return None


def save_weather_to_csv(weather_data):
    """Append one weather record to the CSV file."""
    if not create_csv_if_missing():
        return False

    try:
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    weather_data["date_time"],
                    weather_data["city"],
                    weather_data["temperature_celsius"],
                    weather_data["humidity"],
                    weather_data["pressure"],
                    weather_data["weather_description"],
                    weather_data["wind_speed"],
                ]
            )
    except (KeyError, OSError) as error:
        set_last_error(f"Could not save weather data to CSV: {error}")
        return False

    return True


def fetch_and_save_weather(city):
    """Fetch weather data for a city and save it if the fetch succeeds."""
    weather_data = fetch_weather_data(city)

    if weather_data and save_weather_to_csv(weather_data):
        print("\nWeather data saved successfully!")
        print(f"City: {weather_data['city']}")
        print(f"Temperature: {weather_data['temperature_celsius']} C")
        print(f"Humidity: {weather_data['humidity']}%")
        print(f"Pressure: {weather_data['pressure']} hPa")
        print(f"Condition: {weather_data['weather_description']}")
        print(f"Wind Speed: {weather_data['wind_speed']} m/s")
