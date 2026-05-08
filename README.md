# Weather Data Analyzer

Weather Data Analyzer is a beginner-friendly Streamlit web application that fetches live weather data from the OpenWeatherMap API, stores the data in CSV format, and displays interactive weather charts.

## Project Purpose

This project is suitable for a college mini project because it demonstrates:

- API usage with Python
- CSV file storage
- Data analysis with pandas
- Interactive charts with Plotly
- A modern web dashboard using Streamlit
- Clean modular project organization

## Features

- Search weather by city name
- Fetch live weather data from OpenWeatherMap
- Display weather metric cards for:
  - Temperature
  - Humidity
  - Pressure
  - Weather condition
  - Wind speed
- Store weather history in `data/weather.csv`
- Show interactive charts for:
  - Temperature trends
  - Humidity trends
  - Weather condition frequency
- Sidebar navigation
- Responsive dashboard layout
- Beginner-friendly comments in the code

## Project Structure

```text
weather-data-analyzer/
|-- app.py
|-- fetch_weather.py
|-- analyze.py
|-- visualize.py
|-- data/
|   `-- weather.csv
|-- requirements.txt
`-- README.md
```

`app.py` is the main Streamlit web application. The helper files keep the code modular and easy to understand.

## Installation

From the folder that contains `weather-data-analyzer`, move into the project folder:

```bash
cd weather-data-analyzer
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment.

On Windows:

```bash
venv\Scripts\activate
```

On macOS or Linux:

```bash
source venv/bin/activate
```

Install the required libraries:

```bash
pip install -r requirements.txt
```

## API Usage

This project uses the OpenWeatherMap Current Weather Data API.

The API key is already present in `fetch_weather.py`:

```python
API_KEY = "a197094fcc506fc7b9a0d0fd6dada94f"
```

When a city is searched, the app requests live data from OpenWeatherMap and saves these values:

- Temperature in Celsius
- Humidity
- Pressure
- Weather description
- Wind speed
- Date and time of the request
- City name

## How to Run the Streamlit App

Always run the Streamlit app from inside the `weather-data-analyzer` folder:

```bash
cd weather-data-analyzer
streamlit run app.py
```

If you are already inside the project folder, run:

```bash
streamlit run app.py
```

Streamlit will open the app in your browser. If it does not open automatically, copy the local URL shown in the terminal and paste it into your browser.

## How to Use

1. Open the dashboard.
2. Enter a city name in the search box.
3. Click `Fetch Weather`.
4. View the latest weather metrics.
5. Scroll down to see temperature, humidity, and weather condition charts.
6. Open the `History` page from the sidebar to view saved CSV records.

## CSV Storage

All weather records are saved in:

```text
data/weather.csv
```

The CSV file is automatically created if it is missing.

The project uses a fixed path based on the location of `fetch_weather.py`, so the CSV is saved inside the project's `data` folder.

## Future Improvements

- Add user-selected date filters
- Save charts as image files
- Compare two cities side by side
- Add forecast data for upcoming days
- Use environment variables for the API key
- Deploy the dashboard online with Streamlit Community Cloud
