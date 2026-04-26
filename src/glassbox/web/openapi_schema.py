"""Deterministic OpenAPI schema export for browser type generation."""

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.web.app import create_app


def build_openapi_schema() -> dict[str, Any]:
    """Build the FastAPI OpenAPI schema without starting an HTTP server."""

    with tempfile.TemporaryDirectory(prefix="glassbox-openapi-") as workspace:
        with open_runtime_context(Path(workspace)) as runtime_context:
            return create_app(runtime_context).openapi()


def export_openapi_schema(output_path: Path) -> None:
    """Write the deterministic OpenAPI schema JSON to *output_path*."""

    schema = build_openapi_schema()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the Glassbox FastAPI OpenAPI schema as JSON."
    )
    parser.add_argument("output", type=Path, help="Path to write openapi.json")
    args = parser.parse_args(argv)

    export_openapi_schema(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
