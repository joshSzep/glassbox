"""Runtime logging helpers for Glassbox orchestration flows."""

import logging
from pathlib import Path
from uuid import UUID

_RUNTIME_LOGGER_NAME = "glassbox.runtime"


def configure_runtime_logging() -> logging.Logger:
    """Ensure the runtime logger is safe to use even without app-level handlers."""

    logger = logging.getLogger(_RUNTIME_LOGGER_NAME)
    if not any(isinstance(handler, logging.NullHandler) for handler in logger.handlers):
        logger.addHandler(logging.NullHandler())
    return logger


def get_runtime_logger(name: str) -> logging.Logger:
    """Return a child logger under the Glassbox runtime namespace."""

    configure_runtime_logging()
    return logging.getLogger(f"{_RUNTIME_LOGGER_NAME}.{name}")


def runtime_log_extra(**fields: object) -> dict[str, object]:
    """Normalize common structured fields for runtime log records."""

    normalized: dict[str, object] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, UUID | Path):
            normalized[key] = str(value)
            continue
        normalized[key] = value
    return normalized
