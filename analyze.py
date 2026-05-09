"""
Analyze stored weather data using pandas.

The Streamlit app stores records in SQLite. These helper functions are useful
for local command-line checks and beginner practice.
"""

from database import initialize_database, load_all_weather_history


def load_weather_data():
    """Read weather data from SQLite and return it as a pandas DataFrame."""
    initialize_database()
    data = load_all_weather_history()

    if data.empty:
        print("No weather records found. Log in to the Streamlit app and fetch weather first.")
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
    print(f"Total Records: {len(data)}")
    print(f"Average Temperature: {average_temperature:.2f} C")
    print(f"Highest Temperature: {highest_temperature:.2f} C")
    print(f"Lowest Temperature: {lowest_temperature:.2f} C")
    print(f"Average Humidity: {average_humidity:.2f}%")
    print(f"Most Common Weather Condition: {most_common_condition}")
