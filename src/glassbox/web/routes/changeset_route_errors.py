"""HTTP error helpers for changeset routes."""

from typing import NoReturn
from uuid import UUID

from fastapi import HTTPException


def raise_not_found_from_value_error(exc: ValueError) -> NoReturn:
    raise HTTPException(status_code=404, detail=str(exc)) from exc


def raise_validation_or_not_found_from_value_error(exc: ValueError) -> NoReturn:
    message = str(exc)
    if message.startswith("unknown "):
        raise_not_found_from_value_error(exc)
    raise HTTPException(status_code=422, detail=message) from exc


def raise_unknown_review_feedback(feedback_id: UUID) -> NoReturn:
    raise HTTPException(
        status_code=404,
        detail=f"unknown review feedback: {feedback_id}",
    )


__all__ = [
    "raise_not_found_from_value_error",
    "raise_validation_or_not_found_from_value_error",
    "raise_unknown_review_feedback",
]
