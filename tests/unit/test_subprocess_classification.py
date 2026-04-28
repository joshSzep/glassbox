"""Unit tests for shared subprocess failure classification."""

from glassbox.tools._subprocess import classify_subprocess_failure


def test_classifies_negative_signal_return_code_as_interrupted() -> None:
    assert classify_subprocess_failure(exit_code=-15, timed_out=False) == (
        "interrupted",
        15,
    )


def test_classifies_shell_signal_exit_status_as_interrupted() -> None:
    assert classify_subprocess_failure(exit_code=143, timed_out=False) == (
        "interrupted",
        15,
    )


def test_classifies_regular_nonzero_exit_as_execution_error() -> None:
    assert classify_subprocess_failure(exit_code=42, timed_out=False) == (
        "execution_error",
        None,
    )


def test_classifies_cancelled_subprocess_separately() -> None:
    assert classify_subprocess_failure(
        exit_code=-15,
        timed_out=False,
        cancelled=True,
    ) == ("cancelled", 15)
