"""
Create graphs from stored weather data using matplotlib.

The main web app uses Plotly charts, but this file keeps the beginner-friendly
command-line visualization examples.
"""

import matplotlib.pyplot as plt

from database import initialize_database, load_all_weather_history


def load_weather_data():
    """Read weather data from SQLite and prepare it for graphing."""
    initialize_database()
    data = load_all_weather_history()

    if data.empty:
        print("No weather records found. Log in to the Streamlit app and fetch weather first.")
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
