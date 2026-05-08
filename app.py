"""
Streamlit Weather Data Analyzer

Run this file with:
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from fetch_weather import (
    CSV_FILE,
    create_csv_if_missing,
    fetch_weather_data,
    get_last_error,
    save_weather_to_csv,
)


# -----------------------------
# Page setup and custom styling
# -----------------------------
st.set_page_config(
    page_title="Weather Data Analyzer",
    layout="wide",
)

st.markdown(
    """
    <style>
        .main {
            background-color: #f7f9fc;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        .metric-card {
            background: #ffffff;
            border: 1px solid #e7edf5;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 4px 14px rgba(22, 34, 51, 0.06);
            min-height: 120px;
        }

        .metric-label {
            color: #5d6b82;
            font-size: 0.9rem;
            margin-bottom: 0.4rem;
        }

        .metric-value {
            color: #172033;
            font-size: 1.8rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .metric-note {
            color: #738096;
            font-size: 0.85rem;
            margin-top: 0.35rem;
        }

        .section-title {
            color: #172033;
            font-size: 1.35rem;
            font-weight: 700;
            margin-top: 1.2rem;
            margin-bottom: 0.4rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_weather_history():
    """Load saved weather records from the CSV file."""
    if not create_csv_if_missing():
        st.error(get_last_error() or "Could not prepare the weather CSV file.")
        return pd.DataFrame()

    try:
        data = pd.read_csv(CSV_FILE)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except OSError as error:
        st.error(f"Could not read the weather CSV file: {error}")
        return pd.DataFrame()

    if data.empty:
        return data

    # Convert date_time into a real datetime column for time-based charts.
    data["date_time"] = pd.to_datetime(data["date_time"], errors="coerce")
    data = data.dropna(subset=["date_time"])
    return data


def show_metric_card(label, value, note):
    """Display one custom weather metric card."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_current_weather(weather_data):
    """Show the latest fetched weather details in a responsive card layout."""
    st.markdown('<div class="section-title">Current Weather</div>', unsafe_allow_html=True)

    first_row = st.columns(3)
    second_row = st.columns(2)

    with first_row[0]:
        show_metric_card(
            "Temperature",
            f"{weather_data['temperature_celsius']} C",
            weather_data["city"],
        )

    with first_row[1]:
        show_metric_card("Humidity", f"{weather_data['humidity']}%", "Current air moisture")

    with first_row[2]:
        show_metric_card("Pressure", f"{weather_data['pressure']} hPa", "Atmospheric pressure")

    with second_row[0]:
        show_metric_card(
            "Weather Condition",
            weather_data["weather_description"].title(),
            "OpenWeatherMap live reading",
        )

    with second_row[1]:
        show_metric_card("Wind Speed", f"{weather_data['wind_speed']} m/s", "Measured wind speed")


def show_summary_cards(data):
    """Show quick analysis numbers calculated from the saved history."""
    if data.empty:
        return

    st.markdown('<div class="section-title">History Summary</div>', unsafe_allow_html=True)

    average_temperature = data["temperature_celsius"].mean()
    highest_temperature = data["temperature_celsius"].max()
    average_humidity = data["humidity"].mean()
    most_common_condition = data["weather_description"].mode()
    most_common_condition = most_common_condition[0] if not most_common_condition.empty else "Not available"

    columns = st.columns(4)

    with columns[0]:
        show_metric_card("Average Temperature", f"{average_temperature:.2f} C", "Across all records")
    with columns[1]:
        show_metric_card("Highest Temperature", f"{highest_temperature:.2f} C", "Warmest saved record")
    with columns[2]:
        show_metric_card("Average Humidity", f"{average_humidity:.2f}%", "Across all records")
    with columns[3]:
        show_metric_card("Common Condition", most_common_condition.title(), "Most frequent condition")


def show_weather_charts(data):
    """Create interactive Plotly charts for weather history."""
    if data.empty:
        st.info("No weather history yet. Fetch weather data first to see charts.")
        return

    st.markdown('<div class="section-title">Interactive Weather Charts</div>', unsafe_allow_html=True)

    selected_city = st.selectbox(
        "Filter charts by city",
        options=["All Cities"] + sorted(data["city"].dropna().unique().tolist()),
    )

    if selected_city != "All Cities":
        chart_data = data[data["city"] == selected_city]
    else:
        chart_data = data

    temperature_chart = px.line(
        chart_data,
        x="date_time",
        y="temperature_celsius",
        color="city",
        markers=True,
        title="Temperature Trends",
        labels={
            "date_time": "Date and Time",
            "temperature_celsius": "Temperature (C)",
            "city": "City",
        },
    )

    humidity_chart = px.line(
        chart_data,
        x="date_time",
        y="humidity",
        color="city",
        markers=True,
        title="Humidity Trends",
        labels={
            "date_time": "Date and Time",
            "humidity": "Humidity (%)",
            "city": "City",
        },
    )

    condition_counts = (
        chart_data["weather_description"]
        .value_counts()
        .rename_axis("weather_description")
        .reset_index(name="count")
    )

    condition_chart = px.bar(
        condition_counts,
        x="weather_description",
        y="count",
        title="Weather Condition Frequency",
        labels={
            "weather_description": "Weather Condition",
            "count": "Frequency",
        },
        color="weather_description",
    )

    st.plotly_chart(temperature_chart, use_container_width=True)
    st.plotly_chart(humidity_chart, use_container_width=True)
    st.plotly_chart(condition_chart, use_container_width=True)


def show_history_table(data):
    """Display the saved CSV records inside the dashboard."""
    st.markdown('<div class="section-title">Saved Weather History</div>', unsafe_allow_html=True)

    if data.empty:
        st.info("The CSV file is ready, but no weather records have been saved yet.")
        return

    st.dataframe(data.sort_values("date_time", ascending=False), use_container_width=True)


def dashboard_page():
    """Main dashboard page with search, current weather, summary, and charts."""
    st.title("Weather Data Analyzer")
    st.caption("A modern Streamlit dashboard for live weather collection and analysis.")

    search_col, button_col = st.columns([4, 1])

    with search_col:
        city = st.text_input("Search city", placeholder="Example: Mumbai, London, New York")

    with button_col:
        st.write("")
        st.write("")
        fetch_button = st.button("Fetch Weather", use_container_width=True)

    if fetch_button:
        if not city.strip():
            st.warning("Please enter a city name before fetching weather data.")
        else:
            with st.spinner("Fetching live weather data..."):
                weather_data = fetch_weather_data(city.strip())

            if weather_data:
                saved_successfully = save_weather_to_csv(weather_data)

                if saved_successfully:
                    st.success(f"Weather data for {weather_data['city']} saved successfully.")
                    st.session_state["latest_weather"] = weather_data
                else:
                    st.error(get_last_error() or "Weather data was fetched, but it could not be saved.")
            else:
                st.error(get_last_error() or "Could not fetch weather data. Please try again.")

    if "latest_weather" in st.session_state:
        show_current_weather(st.session_state["latest_weather"])

    history = load_weather_history()
    show_summary_cards(history)
    show_weather_charts(history)


def history_page():
    """Page for viewing the CSV weather history."""
    st.title("Weather History")
    st.caption("These records are loaded from data/weather.csv.")
    show_history_table(load_weather_history())


def about_page():
    """Simple project information page."""
    st.title("About This Project")
    st.write(
        "Weather Data Analyzer is a beginner-friendly college mini project built with "
        "Python, Streamlit, OpenWeatherMap, pandas, and Plotly."
    )
    st.write(
        "The app fetches live weather data, stores each record in CSV format, "
        "and visualizes weather trends through interactive charts."
    )


def main():
    """Control sidebar navigation and display the selected page."""
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "History", "About"])

    st.sidebar.divider()
    st.sidebar.write("Data file:")
    st.sidebar.code(CSV_FILE)

    if page == "Dashboard":
        dashboard_page()
    elif page == "History":
        history_page()
    else:
        about_page()


if __name__ == "__main__":
    main()
