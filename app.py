"""
Professional multi-user Streamlit Weather Data Analyzer.

Run this file with:
    streamlit run app.py
"""

from html import escape
from datetime import datetime

import plotly.express as px
import streamlit as st

from auth import is_logged_in, login_user, logout_user, signup_user
from database import (
    DATABASE_FILE,
    initialize_database,
    load_saved_searches,
    load_weather_history,
    save_weather_record,
)
from fetch_weather import fetch_weather_data, get_last_error


st.set_page_config(
    page_title="Weather Analytics Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_custom_styles():
    """Add the premium dark SaaS theme and custom component styling."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :root {
                --bg: #070a13;
                --panel: rgba(16, 24, 43, 0.72);
                --panel-strong: rgba(20, 31, 54, 0.92);
                --panel-soft: rgba(148, 163, 184, 0.10);
                --border: rgba(190, 208, 235, 0.18);
                --border-bright: rgba(125, 211, 252, 0.42);
                --text: #f4f8ff;
                --muted: #a7b4cb;
                --muted-strong: #cbd5e1;
                --accent: #38bdf8;
                --accent-two: #34d399;
                --accent-three: #a78bfa;
                --warning: #fbbf24;
                --danger: #fb7185;
            }

            .stApp {
                background:
                    radial-gradient(circle at 18% 8%, rgba(56, 189, 248, 0.28), transparent 30%),
                    radial-gradient(circle at 84% 16%, rgba(52, 211, 153, 0.18), transparent 28%),
                    radial-gradient(circle at 55% 92%, rgba(167, 139, 250, 0.16), transparent 24%),
                    linear-gradient(135deg, #060914 0%, #0f172a 48%, #08111f 100%);
                color: var(--text);
                font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }

            .block-container {
                padding-top: 1rem;
                padding-bottom: 2.5rem;
                max-width: 1240px;
            }

            [data-testid="stSidebar"] {
                background: rgba(4, 9, 20, 0.92);
                border-right: 1px solid var(--border);
                backdrop-filter: blur(24px);
            }

            [data-testid="stSidebar"] * {
                color: var(--text);
            }

            [data-testid="stSidebar"] [role="radiogroup"] label {
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 0.45rem 0.65rem;
                margin-bottom: 0.35rem;
                transition: background 180ms ease, border-color 180ms ease, transform 180ms ease;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label:hover {
                background: rgba(56, 189, 248, 0.12);
                border-color: rgba(56, 189, 248, 0.25);
                transform: translateX(3px);
            }

            [data-testid="stSidebar"] [aria-checked="true"] {
                background: linear-gradient(135deg, rgba(56, 189, 248, 0.20), rgba(52, 211, 153, 0.14));
                border-color: var(--border-bright);
                box-shadow: inset 0 0 18px rgba(56, 189, 248, 0.10);
            }

            [data-testid="stSidebar"] hr {
                border-color: var(--border);
            }

            h1, h2, h3, p, label, span {
                color: var(--text);
                letter-spacing: 0;
            }

            .auth-hero {
                max-width: 540px;
                margin: 4vh auto 1.2rem;
                padding: 2.1rem;
                background:
                    linear-gradient(145deg, rgba(15, 23, 42, 0.86), rgba(18, 33, 56, 0.68)),
                    linear-gradient(135deg, rgba(56, 189, 248, 0.16), rgba(52, 211, 153, 0.10));
                border: 1px solid rgba(148, 214, 255, 0.25);
                border-radius: 8px;
                box-shadow: 0 26px 80px rgba(0, 0, 0, 0.38);
                backdrop-filter: blur(24px);
                position: relative;
                overflow: hidden;
            }

            .auth-hero::before {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
                transform: translateX(-100%);
                animation: sheen 5s ease-in-out infinite;
            }

            @keyframes sheen {
                0%, 45% { transform: translateX(-100%); }
                70%, 100% { transform: translateX(100%); }
            }

            .auth-title {
                font-size: clamp(2rem, 5vw, 3rem);
                font-weight: 800;
                margin-bottom: 0.4rem;
                line-height: 1.05;
            }

            .auth-copy {
                color: var(--muted);
                margin-bottom: 0;
                font-size: 1rem;
                line-height: 1.7;
            }

            .auth-badge, .nav-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                padding: 0.35rem 0.65rem;
                border: 1px solid rgba(125, 211, 252, 0.34);
                border-radius: 999px;
                background: rgba(14, 165, 233, 0.12);
                color: #dff6ff;
                font-size: 0.82rem;
                font-weight: 700;
                margin-bottom: 1rem;
            }

            div[data-testid="stForm"] {
                max-width: 540px;
                margin: 0 auto;
                padding: 1.35rem;
                border: 1px solid var(--border);
                border-radius: 8px;
                background: rgba(7, 12, 25, 0.62);
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
                backdrop-filter: blur(20px);
                transition: border-color 180ms ease, transform 180ms ease;
            }

            div[data-testid="stForm"]:hover {
                border-color: rgba(125, 211, 252, 0.32);
                transform: translateY(-1px);
            }

            .top-nav {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: 0.85rem 1rem;
                margin-bottom: 1.15rem;
                background: rgba(8, 13, 27, 0.72);
                border: 1px solid var(--border);
                border-radius: 8px;
                box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
                backdrop-filter: blur(22px);
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                min-width: 0;
            }

            .brand-mark {
                width: 42px;
                height: 42px;
                display: grid;
                place-items: center;
                border-radius: 8px;
                background: linear-gradient(135deg, #0ea5e9, #22c55e);
                box-shadow: 0 0 28px rgba(56, 189, 248, 0.32);
                font-size: 1.25rem;
            }

            .brand-title {
                font-size: 1rem;
                font-weight: 800;
                color: var(--text);
            }

            .brand-subtitle {
                font-size: 0.8rem;
                color: var(--muted);
                margin-top: 0.1rem;
            }

            .nav-right {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 0.7rem;
            }

            .dashboard-title {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1.1rem;
                padding: 1.55rem;
                border: 1px solid rgba(125, 211, 252, 0.24);
                border-radius: 8px;
                background:
                    linear-gradient(145deg, rgba(15, 23, 42, 0.78), rgba(20, 41, 66, 0.58)),
                    radial-gradient(circle at 80% 20%, rgba(56, 189, 248, 0.24), transparent 28%);
                box-shadow: 0 22px 70px rgba(0, 0, 0, 0.28);
                backdrop-filter: blur(24px);
                overflow: hidden;
            }

            .hero-kicker {
                color: #b8efff;
                font-size: 0.86rem;
                font-weight: 800;
                text-transform: uppercase;
                margin-bottom: 0.55rem;
            }

            .dashboard-title h1 {
                font-size: clamp(2rem, 4vw, 3.35rem);
                line-height: 1.03;
                margin: 0 0 0.55rem;
            }

            .dashboard-title p {
                color: var(--muted-strong);
                margin: 0;
                line-height: 1.65;
            }

            .hero-weather {
                min-width: 220px;
                padding: 1rem;
                border: 1px solid var(--border);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.08);
                text-align: right;
                box-shadow: inset 0 0 24px rgba(255, 255, 255, 0.04);
            }

            .hero-icon {
                font-size: 2.5rem;
                line-height: 1;
            }

            .hero-city {
                font-size: 1.25rem;
                font-weight: 800;
                margin-top: 0.5rem;
            }

            .hero-time {
                color: var(--muted);
                font-size: 0.86rem;
                margin-top: 0.25rem;
            }

            .section-title {
                font-size: 1.1rem;
                font-weight: 750;
                margin: 1.55rem 0 0.75rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .glass-card {
                min-height: 150px;
                padding: 1.1rem;
                background:
                    linear-gradient(145deg, rgba(15, 23, 42, 0.78), rgba(30, 41, 59, 0.48)),
                    var(--panel);
                border: 1px solid rgba(148, 214, 255, 0.18);
                border-radius: 8px;
                box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
                backdrop-filter: blur(20px);
                position: relative;
                overflow: hidden;
                transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
            }

            .glass-card::before {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(135deg, var(--card-glow, rgba(56, 189, 248, 0.18)), transparent 45%);
                opacity: 0.75;
                pointer-events: none;
            }

            .glass-card:hover {
                transform: translateY(-4px);
                border-color: var(--card-border, rgba(125, 211, 252, 0.48));
                box-shadow: 0 22px 70px rgba(0, 0, 0, 0.36), 0 0 32px var(--card-shadow, rgba(56, 189, 248, 0.18));
            }

            .metric-top {
                position: relative;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.8rem;
            }

            .metric-icon {
                width: 46px;
                height: 46px;
                display: grid;
                place-items: center;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.14);
                font-size: 1.45rem;
            }

            .metric-label {
                position: relative;
                color: var(--muted);
                font-size: 0.82rem;
                font-weight: 700;
                text-transform: uppercase;
            }

            .metric-value {
                position: relative;
                color: var(--text);
                font-size: clamp(1.5rem, 3vw, 2.05rem);
                font-weight: 800;
                line-height: 1.15;
                overflow-wrap: anywhere;
                margin-top: 1.1rem;
            }

            .metric-note {
                position: relative;
                color: var(--muted);
                font-size: 0.82rem;
                margin-top: 0.45rem;
            }

            .metric-blue {
                --card-glow: rgba(56, 189, 248, 0.24);
                --card-border: rgba(56, 189, 248, 0.56);
                --card-shadow: rgba(56, 189, 248, 0.26);
            }

            .metric-green {
                --card-glow: rgba(52, 211, 153, 0.22);
                --card-border: rgba(52, 211, 153, 0.54);
                --card-shadow: rgba(52, 211, 153, 0.22);
            }

            .metric-violet {
                --card-glow: rgba(167, 139, 250, 0.22);
                --card-border: rgba(167, 139, 250, 0.54);
                --card-shadow: rgba(167, 139, 250, 0.22);
            }

            .metric-amber {
                --card-glow: rgba(251, 191, 36, 0.20);
                --card-border: rgba(251, 191, 36, 0.48);
                --card-shadow: rgba(251, 191, 36, 0.18);
            }

            .saved-search {
                display: inline-flex;
                align-items: center;
                margin: 0 0.45rem 0.55rem 0;
                padding: 0.5rem 0.75rem;
                border: 1px solid var(--border);
                border-radius: 999px;
                background: rgba(148, 163, 184, 0.12);
                color: var(--text);
                font-size: 0.9rem;
                transition: transform 160ms ease, border-color 160ms ease;
            }

            .saved-search:hover {
                transform: translateY(-2px);
                border-color: rgba(125, 211, 252, 0.42);
            }

            .stTextInput input {
                background: rgba(7, 12, 25, 0.78);
                color: var(--text);
                border: 1px solid var(--border);
                border-radius: 8px;
                min-height: 2.75rem;
                transition: border-color 160ms ease, box-shadow 160ms ease;
            }

            .stTextInput input:focus {
                border-color: rgba(56, 189, 248, 0.70);
                box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.10);
            }

            .stButton > button {
                border-radius: 8px;
                border: 1px solid rgba(125, 211, 252, 0.45);
                background: linear-gradient(135deg, #0284c7, #16a34a);
                color: white;
                font-weight: 700;
                min-height: 2.7rem;
                box-shadow: 0 12px 32px rgba(14, 165, 233, 0.20);
                transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
            }

            .stButton > button:hover {
                border-color: rgba(186, 230, 253, 0.9);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 16px 42px rgba(34, 197, 94, 0.24);
            }

            .stSelectbox [data-baseweb="select"] > div,
            .stDataFrame {
                border-radius: 8px;
            }

            .chart-shell {
                padding: 0.4rem 0;
            }

            .footer {
                margin-top: 2rem;
                padding: 1rem;
                border: 1px solid var(--border);
                border-radius: 8px;
                background: rgba(7, 12, 25, 0.50);
                color: var(--muted);
                text-align: center;
                font-size: 0.86rem;
            }

            [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
                color: var(--text);
            }

            @media (max-width: 700px) {
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }

                .auth-hero {
                    margin-top: 1rem;
                    padding: 1.25rem;
                }

                div[data-testid="stForm"] {
                    padding: 1rem;
                }

                .top-nav, .dashboard-title {
                    display: block;
                }

                .nav-right, .hero-weather {
                    margin-top: 0.9rem;
                    text-align: left;
                    justify-content: flex-start;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_metric_card(label, value, note, icon="✦", style="metric-blue"):
    """Display one glassmorphism weather metric card."""
    st.markdown(
        f"""
        <div class="glass-card {escape(str(style))}">
            <div class="metric-top">
                <div class="metric-label">{escape(str(label))}</div>
                <div class="metric-icon">{escape(str(icon))}</div>
            </div>
            <div class="metric-value">{escape(str(value))}</div>
            <div class="metric-note">{escape(str(note))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_auth_header(title, copy):
    """Show a consistent header for login and signup pages."""
    st.markdown(
        f"""
        <div class="auth-hero">
            <div class="auth-badge">☁️ Premium weather intelligence</div>
            <div class="auth-title">{escape(str(title))}</div>
            <div class="auth-copy">{escape(str(copy))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_pending_toast():
    """Show a toast message requested before a rerun."""
    toast = st.session_state.pop("toast", None)
    if toast:
        st.toast(toast["message"], icon=toast.get("icon"))


def queue_toast(message, icon="✅"):
    """Store a toast so it survives Streamlit reruns."""
    st.session_state["toast"] = {"message": message, "icon": icon}


def weather_icon(description):
    """Pick a friendly weather icon from an OpenWeatherMap description."""
    text = str(description or "").lower()
    if "storm" in text or "thunder" in text:
        return "⛈️"
    if "rain" in text or "drizzle" in text:
        return "🌧️"
    if "snow" in text:
        return "❄️"
    if "cloud" in text:
        return "☁️"
    if "mist" in text or "fog" in text or "haze" in text:
        return "🌫️"
    if "clear" in text:
        return "☀️"
    return "🌤️"


def render_top_nav():
    """Render the premium top navigation bar."""
    safe_username = escape(str(st.session_state["username"]))
    st.markdown(
        f"""
        <div class="top-nav">
            <div class="brand">
                <div class="brand-mark">☁️</div>
                <div>
                    <div class="brand-title">Weather Analytics</div>
                    <div class="brand-subtitle">Live climate insights dashboard</div>
                </div>
            </div>
            <div class="nav-right">
                <div class="nav-pill">👤 {safe_username}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def login_page():
    """Render the login page."""
    show_auth_header(
        "Weather Analytics",
        "Log in to view your saved searches, live weather cards, and private history.",
    )

    with st.form("login_form"):
        identifier = st.text_input("Username or email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)

    if submitted:
        if not identifier.strip() or not password:
            st.warning("Please enter your username/email and password.")
        else:
            success, message = login_user(identifier, password)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.info("New here? Choose Sign Up from the sidebar to create your account.")


def signup_page():
    """Render the signup page."""
    show_auth_header(
        "Create Account",
        "Your weather history is stored privately and follows you after login.",
    )

    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Sign Up", use_container_width=True)

    if submitted:
        success, message = signup_user(username, email, password, confirm_password)
        if success:
            st.success(message)
        else:
            st.error(message)

    st.info("Already have an account? Choose Login from the sidebar.")


def show_saved_searches(user_id):
    """Display recent unique city searches for the logged-in user."""
    searches = load_saved_searches(user_id)
    st.markdown('<div class="section-title">Saved Searches</div>', unsafe_allow_html=True)

    if not searches:
        st.info("Saved searches will appear here after you fetch a city.")
        return

    chips = "".join(
        f'<span class="saved-search">{escape(str(row["city"]))}</span>'
        for row in searches
    )
    st.markdown(chips, unsafe_allow_html=True)


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
    """Show quick analysis numbers calculated from the user's saved history."""
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
        show_metric_card("Average Temperature", f"{average_temperature:.2f} C", "Your saved records")
    with columns[1]:
        show_metric_card("Highest Temperature", f"{highest_temperature:.2f} C", "Warmest saved record")
    with columns[2]:
        show_metric_card("Average Humidity", f"{average_humidity:.2f}%", "Your saved records")
    with columns[3]:
        show_metric_card("Common Condition", most_common_condition.title(), "Most frequent condition")


def show_weather_charts(data):
    """Create interactive Plotly charts for the user's weather history."""
    if data.empty:
        st.info("No weather history yet. Fetch weather data first to see charts.")
        return

    st.markdown('<div class="section-title">Interactive Weather Charts</div>', unsafe_allow_html=True)

    selected_city = st.selectbox(
        "Filter charts by city",
        options=["All Cities"] + sorted(data["city"].dropna().unique().tolist()),
    )
    chart_data = data if selected_city == "All Cities" else data[data["city"] == selected_city]

    chart_template = "plotly_dark"
    temperature_chart = px.line(
        chart_data,
        x="date_time",
        y="temperature_celsius",
        color="city",
        markers=True,
        title="Temperature Trends",
        labels={"date_time": "Date and Time", "temperature_celsius": "Temperature (C)", "city": "City"},
        template=chart_template,
    )

    humidity_chart = px.line(
        chart_data,
        x="date_time",
        y="humidity",
        color="city",
        markers=True,
        title="Humidity Trends",
        labels={"date_time": "Date and Time", "humidity": "Humidity (%)", "city": "City"},
        template=chart_template,
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
        labels={"weather_description": "Weather Condition", "count": "Frequency"},
        color="weather_description",
        template=chart_template,
    )

    for chart in [temperature_chart, humidity_chart, condition_chart]:
        chart.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#edf3ff",
        )
        st.plotly_chart(chart, use_container_width=True)


def show_history_table(data):
    """Display the user's saved database records."""
    st.markdown('<div class="section-title">Saved Weather History</div>', unsafe_allow_html=True)

    if data.empty:
        st.info("No saved weather records yet.")
        return

    display_data = data.drop(columns=["id"], errors="ignore")
    st.dataframe(display_data, use_container_width=True, hide_index=True)


def dashboard_page():
    """Main dashboard page with search, current weather, summary, and charts."""
    user_id = st.session_state["user_id"]
    username = st.session_state["username"]
    safe_username = escape(str(username))

    st.markdown(
        f"""
        <div class="dashboard-title">
            <div>
                <h1>Welcome, {safe_username}</h1>
                <p>Live weather intelligence with your private saved history.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
            with st.spinner("Fetching live weather data and saving it to your account..."):
                weather_data = fetch_weather_data(city.strip())

            if weather_data:
                save_weather_record(user_id, weather_data)
                st.session_state["latest_weather"] = weather_data
                st.success(f"Weather data for {weather_data['city']} saved to your account.")
            else:
                st.error(get_last_error() or "Could not fetch weather data. Please try again.")

    if "latest_weather" in st.session_state:
        show_current_weather(st.session_state["latest_weather"])

    history = load_weather_history(user_id)
    show_saved_searches(user_id)
    show_summary_cards(history)
    show_weather_charts(history)


def history_page():
    """Page for viewing the logged-in user's weather history."""
    st.title("Weather History")
    st.caption("Only records saved by your account are shown here.")
    show_history_table(load_weather_history(st.session_state["user_id"]))


def account_page():
    """Simple account page with logout controls."""
    st.title("Account")
    st.write(f"Username: **{st.session_state['username']}**")
    st.write(f"Email: **{st.session_state['email']}**")
    st.caption(f"Database: {DATABASE_FILE}")

    if st.button("Log Out", use_container_width=True):
        logout_user()
        st.success("You have been logged out.")
        st.rerun()


def about_page():
    """Simple project information page."""
    st.title("About This Project")
    st.write(
        "Weather Analytics Platform is a multi-user Streamlit application with "
        "secure authentication, SQLite storage, OpenWeatherMap integration, and "
        "private user-specific weather dashboards."
    )


def public_navigation():
    """Sidebar shown before login."""
    st.sidebar.title("Weather Analytics")
    return st.sidebar.radio("Account", ["Login", "Sign Up"])


def private_navigation():
    """Sidebar shown after login."""
    st.sidebar.title("Weather Analytics")
    st.sidebar.caption(f"Signed in as {st.session_state['username']}")
    page = st.sidebar.radio("Go to", ["Dashboard", "History", "Account", "About"])
    st.sidebar.divider()

    if st.sidebar.button("Log Out", use_container_width=True):
        logout_user()
        st.rerun()

    return page


def main():
    """Initialize storage, route pages, and keep users logged in per session."""
    initialize_database()
    apply_custom_styles()

    if not is_logged_in():
        page = public_navigation()
        if page == "Login":
            login_page()
        else:
            signup_page()
        return

    page = private_navigation()
    if page == "Dashboard":
        dashboard_page()
    elif page == "History":
        history_page()
    elif page == "Account":
        account_page()
    else:
        about_page()


if __name__ == "__main__":
    main()
