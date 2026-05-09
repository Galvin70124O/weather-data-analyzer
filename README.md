# Weather Analytics Platform

Weather Analytics Platform is a professional multi-user Streamlit web app for live weather collection and analysis. It includes account creation, secure login, private user dashboards, SQLite cloud-ready storage, OpenWeatherMap integration, and interactive Plotly charts.

## Features

- Sign up, login, and logout pages
- Session-based login using Streamlit session state
- Salted password hashing with PBKDF2
- Duplicate username and email protection
- Private weather history for each user
- Live OpenWeatherMap current weather lookups
- Saved searches and personalized dashboard greeting
- Dark professional UI with glass-style weather cards
- Interactive temperature, humidity, and weather condition charts
- SQLite database storage in `data/weather_app.db`
- Render-compatible environment variable support

## Project Structure

```text
weather-data-analyzer/
|-- app.py
|-- auth.py
|-- database.py
|-- fetch_weather.py
|-- analyze.py
|-- visualize.py
|-- data/
|   `-- weather.csv
|-- .env.example
|-- .gitignore
|-- requirements.txt
`-- README.md
```

`app.py` is the main Streamlit application. `auth.py` handles signup, login, logout, and password hashing. `database.py` owns the SQLite tables and user-specific weather queries.

## Database Tables

The app creates these tables automatically when it starts:

- `users`: stores username, email, password hash, and creation time
- `weather_history`: stores weather records linked to `users.id`

Each dashboard query filters by the logged-in user's ID, so users only see their own saved weather data.

## Installation

From the folder that contains `weather-data-analyzer`, move into the project folder:

```bash
cd weather-data-analyzer
```

Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

On macOS or Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## API Key

The app reads the OpenWeatherMap API key from an environment variable:

```text
OPENWEATHER_API_KEY
```

For local development, create a `.env` file from the sample:

```bash
copy .env.example .env
```

Then edit `.env`:

```text
OPENWEATHER_API_KEY=your_real_openweathermap_key
```

The `.env` file is ignored by Git and must not be committed.

## Run Locally

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit.

## How to Use

1. Open the app.
2. Create an account from the Sign Up page.
3. Log in with your username or email.
4. Search for a city on the dashboard.
5. View current weather, saved searches, charts, and your private history.
6. Use the Account page or sidebar button to log out.

## Render Deployment Notes

Use this start command on Render:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Add this environment variable:

```text
OPENWEATHER_API_KEY=your_openweathermap_key
```

Render environment variables are available directly through `os.getenv`, so no `.env` file is needed on Render.

SQLite writes to `data/weather_app.db` by default. To keep user accounts and history after redeploys, attach a Render persistent disk and set:

```text
WEATHER_DATABASE_FILE=/path/to/persistent/weather_app.db
```

## Security Notes

Passwords are salted and hashed before storage. The app validates login credentials with secure hash comparison and prevents duplicate usernames or emails. API keys are loaded from environment variables with `python-dotenv` locally and Render environment variables in production. Do not store real production secrets directly in source code.
