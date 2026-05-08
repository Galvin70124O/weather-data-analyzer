"""
Create graphs from stored weather data using matplotlib.
"""

import matplotlib.pyplot as plt
import pandas as pd

from fetch_weather import CSV_FILE, create_csv_if_missing


def load_weather_data():
    """Read weather data and prepare the date_time column for graphing."""
    if not create_csv_if_missing():
        print("Could not prepare the weather CSV file.")
        return None

    try:
        data = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print("No weather data found. Please fetch weather data first.")
        return None
    except pd.errors.EmptyDataError:
        print("The weather CSV file is empty. Please fetch weather data first.")
        return None
    except OSError as error:
        print(f"Could not read the weather CSV file: {error}")
        return None

    if data.empty:
        print("No weather records found. Please fetch weather data first.")
        return None

    # Convert text dates into real date-time values so matplotlib can plot them.
    data["date_time"] = pd.to_datetime(data["date_time"], errors="coerce")
    data = data.dropna(subset=["date_time"])

    if data.empty:
        print("No valid date-time records found. Please fetch weather data again.")
        return None

    return data


def create_temperature_trend(data):
    """Create a line graph showing temperature changes over time."""
    plt.figure(figsize=(10, 5))
    plt.plot(
        data["date_time"],
        data["temperature_celsius"],
        marker="o",
        color="tomato",
        linewidth=2,
    )
    plt.title("Temperature Trend Over Time")
    plt.xlabel("Date and Time")
    plt.ylabel("Temperature (C)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def create_humidity_bar_graph(data):
    """Create a bar graph showing humidity for each saved record."""
    plt.figure(figsize=(10, 5))
    plt.bar(data["date_time"].astype(str), data["humidity"], color="skyblue")
    plt.title("Humidity Levels")
    plt.xlabel("Date and Time")
    plt.ylabel("Humidity (%)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def create_weather_condition_chart(data):
    """Create a chart showing how often each weather condition appears."""
    condition_counts = data["weather_description"].value_counts()

    plt.figure(figsize=(8, 5))
    condition_counts.plot(kind="bar", color="mediumseagreen")
    plt.title("Weather Condition Frequency")
    plt.xlabel("Weather Condition")
    plt.ylabel("Frequency")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()


def create_weather_graphs():
    """Load data and create all weather graphs."""
    data = load_weather_data()

    if data is None:
        return

    create_temperature_trend(data)
    create_humidity_bar_graph(data)
    create_weather_condition_chart(data)
