"""
Authentication helpers for the Streamlit weather app.

Passwords are never stored directly. They are salted and hashed with PBKDF2,
which is available in Python's standard library.
"""

import hashlib
import hmac
import os
import re

import streamlit as st

from database import create_user, get_user_by_login


HASH_ITERATIONS = 260_000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password):
    """Create a salted password hash suitable for database storage."""
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )
    return f"{HASH_ITERATIONS}${salt.hex()}${password_hash.hex()}"


def verify_password(password, stored_password_hash):
    """Safely compare a password with a stored salted hash."""
    try:
        iterations, salt_hex, hash_hex = stored_password_hash.split("$")
        expected_hash = bytes.fromhex(hash_hex)
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(actual_hash, expected_hash)
    except (ValueError, TypeError):
        return False


def validate_signup(username, email, password, confirm_password):
    """Return a user-friendly validation message, or an empty string if valid."""
    if len(username.strip()) < 3:
        return "Username must be at least 3 characters long."
    if not EMAIL_PATTERN.match(email.strip()):
        return "Please enter a valid email address."
    if len(password) < 6:
        return "Password must be at least 6 characters long."
    if password != confirm_password:
        return "Passwords do not match."
    return ""


def signup_user(username, email, password, confirm_password):
    """Validate and create a new user account."""
    validation_error = validate_signup(username, email, password, confirm_password)
    if validation_error:
        return False, validation_error

    return create_user(username, email, hash_password(password))


def login_user(identifier, password):
    """Check credentials and store the logged-in user in session state."""
    user = get_user_by_login(identifier)

    if user is None or not verify_password(password, user["password_hash"]):
        return False, "Invalid username/email or password."

    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["username"] = user["username"]
    st.session_state["email"] = user["email"]
    return True, "Logged in successfully."


def logout_user():
    """Clear login details from Streamlit session state."""
    for key in ["authenticated", "user_id", "username", "email", "latest_weather"]:
        st.session_state.pop(key, None)


def is_logged_in():
    """Return True when the current Streamlit session has a logged-in user."""
    return bool(st.session_state.get("authenticated") and st.session_state.get("user_id"))
