"""Validate generated frontend release assets before packaging."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from glassbox.web.spa_static import validate_spa_static_assets

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_API_FILES = (
    Path("frontend/generated/openapi.json"),
    Path("frontend/generated/api-types.ts"),
)
STATIC_NEXT_DIR = Path("src/glassbox/web/static_next")


def validate_frontend_release_assets(repo_root: Path = REPO_ROOT) -> list[str]:
    """Return frontend release-asset problems for *repo_root*."""

    problems: list[str] = []
    for relative_path in GENERATED_API_FILES:
        path = repo_root / relative_path
        if not path.is_file():
            problems.append(f"missing generated API file: {relative_path}")

    static_root = repo_root / STATIC_NEXT_DIR
    problems.extend(validate_spa_static_assets(static_root))
    next_root = static_root / "_next"
    if not any(path.is_file() for path in next_root.rglob("*")):
        problems.append(f"missing SPA _next static assets: {STATIC_NEXT_DIR / '_next'}")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate generated frontend release assets."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root to validate; defaults to this checkout",
    )
    args = parser.parse_args(argv)

    problems = validate_frontend_release_assets(args.repo_root.resolve())
    if problems:
        print("Frontend release asset validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    print("Frontend release assets are present and internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
