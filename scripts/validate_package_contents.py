"""Validate built Glassbox wheel and sdist contents."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"

WHEEL_REQUIRED_FILES = (
    "glassbox/__init__.py",
    "glassbox/cli/__init__.py",
    "glassbox/web/app.py",
    "glassbox/web/static_next/index.html",
)
WHEEL_REQUIRED_PREFIXES = ("glassbox/web/static_next/_next/",)
SDIST_REQUIRED_SUFFIXES = (
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "docs/getting-started.md",
    "docs/providers.md",
    "docs/release-packaging.md",
    "docs/v7-release-candidate.md",
    "docs/v7-release-gate.md",
    "docs/manual-v7-release-validation.md",
    "docs/workspace-profiles.md",
    "docs/manual-qa-evidence-v7.md",
    "src/glassbox/web/static_next/index.html",
)
SDIST_REQUIRED_PREFIXES = ("src/glassbox/web/static_next/_next/",)


def validate_distribution_contents(dist_dir: Path = DIST_DIR) -> list[str]:
    """Return package content problems for the newest wheel and sdist."""

    problems: list[str] = []
    wheel_path = _latest_file(dist_dir, "glassbox-*.whl")
    sdist_path = _latest_file(dist_dir, "glassbox-*.tar.gz")
    if wheel_path is None:
        problems.append(f"missing built wheel in {dist_dir}")
    else:
        problems.extend(validate_wheel_contents(wheel_path))
    if sdist_path is None:
        problems.append(f"missing built sdist in {dist_dir}")
    else:
        problems.extend(validate_sdist_contents(sdist_path))
    return problems


def validate_wheel_contents(wheel_path: Path) -> list[str]:
    """Return content problems for one built wheel."""

    problems: list[str] = []
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
        for required_file in WHEEL_REQUIRED_FILES:
            if required_file not in names:
                problems.append(f"wheel missing required file: {required_file}")
        for required_prefix in WHEEL_REQUIRED_PREFIXES:
            if not _has_file_with_prefix(names, required_prefix):
                problems.append(f"wheel missing required file under: {required_prefix}")

        metadata_name = _single_matching_name(names, ".dist-info/METADATA")
        entry_points_name = _single_matching_name(names, ".dist-info/entry_points.txt")
        if metadata_name is None:
            problems.append("wheel missing dist-info METADATA")
        else:
            metadata = wheel.read(metadata_name).decode("utf-8", errors="replace")
            if "Requires-Dist: textual" not in metadata:
                problems.append("wheel metadata missing textual runtime dependency")
            if ">=6" not in metadata or "<7" not in metadata:
                problems.append("wheel metadata missing textual >=6,<7 bounds")
        if entry_points_name is None:
            problems.append("wheel missing console script entry_points.txt")
        else:
            entry_points = wheel.read(entry_points_name).decode(
                "utf-8",
                errors="replace",
            )
            if "glassbox = glassbox.cli:main" not in entry_points:
                problems.append("wheel missing glassbox console script entrypoint")
    return problems


def validate_sdist_contents(sdist_path: Path) -> list[str]:
    """Return content problems for one built source distribution."""

    problems: list[str] = []
    with tarfile.open(sdist_path, mode="r:gz") as sdist:
        names = {member.name for member in sdist.getmembers() if member.isfile()}
    for required_suffix in SDIST_REQUIRED_SUFFIXES:
        if not _has_file_with_suffix(names, required_suffix):
            problems.append(f"sdist missing required file: {required_suffix}")
    for required_prefix in SDIST_REQUIRED_PREFIXES:
        if not _has_file_containing_prefix(names, required_prefix):
            problems.append(f"sdist missing required file under: {required_prefix}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate built Glassbox wheel and sdist contents."
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=DIST_DIR,
        help="directory containing built distribution artifacts",
    )
    args = parser.parse_args(argv)

    problems = validate_distribution_contents(args.dist_dir.resolve())
    if problems:
        print("Package content validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    print("Built wheel and sdist contain required Glassbox release files.")
    return 0


def _latest_file(directory: Path, pattern: str) -> Path | None:
    paths = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not paths:
        return None
    return paths[-1]


def _has_file_with_prefix(names: set[str], prefix: str) -> bool:
    return any(name.startswith(prefix) and not name.endswith("/") for name in names)


def _has_file_with_suffix(names: set[str], suffix: str) -> bool:
    return any(name == suffix or name.endswith(f"/{suffix}") for name in names)


def _has_file_containing_prefix(names: set[str], prefix: str) -> bool:
    return any(f"/{prefix}" in name and not name.endswith("/") for name in names)


def _single_matching_name(names: set[str], suffix: str) -> str | None:
    matches = sorted(name for name in names if name.endswith(suffix))
    return matches[0] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
