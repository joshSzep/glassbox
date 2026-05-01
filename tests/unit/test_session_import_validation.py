"""Focused tests for session import validation helpers."""

import pytest

from glassbox.runtime.session_import_events import parse_optional_uuid
from glassbox.runtime.session_import_events import parse_uuid
from glassbox.runtime.session_import_validation import contains_unredacted_secret


def test_session_import_validation_allows_redacted_secret_placeholders() -> None:
    assert contains_unredacted_secret("OPENAI_API_KEY=<redacted>") is False
    assert contains_unredacted_secret("handoff note without secret material") is False


def test_session_import_validation_rejects_unredacted_secret_material() -> None:
    assert contains_unredacted_secret("OPENAI_API_KEY=sk-live-secret-value") is True
    assert contains_unredacted_secret("raw token sk-secret-value-123456") is True


def test_session_import_event_uuid_parser_labels_invalid_package_fields() -> None:
    with pytest.raises(ValueError, match="invalid message_id in session export"):
        parse_uuid("not-a-uuid", kind="message_id")

    assert parse_optional_uuid(None, kind="forked_from_turn_id") is None
