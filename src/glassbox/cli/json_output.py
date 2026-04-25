"""Shared JSON formatting helpers for CLI commands."""

import json


def format_json_output(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def print_json_output(payload: object) -> None:
    print(format_json_output(payload))
