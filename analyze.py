"""
Analyze stored weather data using pandas.
"""

import pandas as pd

from fetch_weather import CSV_FILE, create_csv_if_missing


def load_weather_data():
    """Read the weather CSV file and return it as a pandas DataFrame."""
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

    return data


def analyze_weather_data():
    """Display useful statistics from the saved weather data."""
    data = load_weather_data()

    if data is None:
        return

    average_temperature = data["temperature_celsius"].mean()
    highest_temperature = data["temperature_celsius"].max()
    lowest_temperature = data["temperature_celsius"].min()
    average_humidity = data["humidity"].mean()
    most_common_condition = data["weather_description"].mode()
    most_common_condition = most_common_condition[0] if not most_common_condition.empty else "Not available"

    print("\n===== Weather Data Analysis =====")
    print(f"Average Temperature: {average_temperature:.2f} C")
    print(f"Highest Temperature: {highest_temperature:.2f} C")
    print(f"Lowest Temperature: {lowest_temperature:.2f} C")
    print(f"Average Humidity: {average_humidity:.2f}%")
    print(f"Most Common Weather Condition: {most_common_condition}")
