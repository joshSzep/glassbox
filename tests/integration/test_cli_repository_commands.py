"""CLI coverage for repository intelligence commands."""

import json
from pathlib import Path

from glassbox.cli import main


def test_repo_index_build_status_search_and_show_commands(
    tmp_path: Path,
    capsys,
) -> None:
    _seed_repository(tmp_path)

    build_exit = main(
        [
            "repo",
            "index",
            "build",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    build_payload = json.loads(capsys.readouterr().out)
    symbol_id = next(
        entry["entry_id"]
        for entry in build_payload["entries"]
        if entry["symbol"] == "UsefulThing"
    )

    status_exit = main(
        [
            "repo",
            "index",
            "status",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    status_payload = json.loads(capsys.readouterr().out)

    search_exit = main(
        [
            "repo",
            "index",
            "search",
            "useful",
            "--cwd",
            str(tmp_path),
            "--limit",
            "1",
            "--json",
        ]
    )
    search_payload = json.loads(capsys.readouterr().out)

    show_exit = main(
        [
            "repo",
            "index",
            "show",
            symbol_id,
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    show_payload = json.loads(capsys.readouterr().out)

    assert build_exit == 0
    assert build_payload["status"] == "fresh"
    assert status_exit == 0
    assert status_payload["status"] == "fresh"
    assert status_payload["entry_count"] == len(build_payload["entries"])
    assert search_exit == 0
    assert len(search_payload) == 1
    assert search_payload[0]["symbol"] == "UsefulThing"
    assert show_exit == 0
    assert show_payload["entry_id"] == symbol_id


def test_repo_index_status_reports_missing_snapshot(tmp_path: Path, capsys) -> None:
    status_exit = main(
        [
            "repo",
            "index",
            "status",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    status_payload = json.loads(capsys.readouterr().out)

    assert status_exit == 0
    assert status_payload["status"] == "missing"
    assert status_payload["entry_count"] == 0


def _seed_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n',
        encoding="utf-8",
    )
