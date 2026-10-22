"""
Logging setup. Most importantly: API keys must never reach the logs.

httpx logs every request at INFO level WITH the full URL, and OpenWeatherMap's key is a URL
parameter (appid=...). The filter below replaces the key with *** in every httpx/httpcore
log line, whatever level the logs are set to.
"""
import logging
import re

SECRET_PARAMS = re.compile(r"((?:appid|api_key|apikey|key|token)=)[^&\s\"']+", re.IGNORECASE)


def redact(text: str) -> str:
    return SECRET_PARAMS.sub(r"\1***", text)


class RedactSecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = redact(message)
        if redacted != message:
            record.msg, record.args = redacted, ()
        return True


def configure_logging() -> None:
    for name in ("httpx", "httpcore"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactSecretsFilter) for f in logger.filters):
            logger.addFilter(RedactSecretsFilter())
        # Request lines aren't useful in production logs; warnings and errors still show
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.WARNING)
