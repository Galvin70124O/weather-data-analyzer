"""Errors from outside services, turned into friendly HTTP answers in app/main.py."""


class UpstreamError(Exception):
    """An outside API (OpenWeatherMap, Open-Meteo) didn't give a usable answer."""

    status_code = 503
    public_message = "The weather service is unavailable right now. Please try again in a minute."


class UpstreamNotConfigured(UpstreamError):
    public_message = "The weather service isn't configured on this server."


class UpstreamNotFound(UpstreamError):
    status_code = 404
    public_message = "The weather service has no data for this place."
