"""CLI coverage for repository intelligence commands."""

import json
from pathlib import Path

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


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

    inspect_exit = main(
        [
            "repo",
            "index",
            "inspect",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    inspect_payload = json.loads(capsys.readouterr().out)

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
    assert status_payload["schema_version"] == 2
    assert status_payload["package_boundary_count"] >= 1
    assert status_payload["source_root_count"] >= 1
    assert status_payload["command_recipe_count"] == len(
        build_payload["command_recipes"]
    )
    assert status_payload["detail"] == (
        "Repository intelligence is fresh for the current source digest."
    )
    assert status_payload["current_source_digest"] == status_payload["source_digest"]
    assert inspect_exit == 0
    assert inspect_payload["schema_version"] == 2
    assert inspect_payload["package_boundaries"][0]["package_id"] == "package:fixture"
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
    assert status_payload["detail"].startswith("No repository index exists")
    assert status_payload["next_actions"] == [
        f"glassbox repo index build --cwd {tmp_path.resolve()}",
    ]


def test_repo_topology_build_status_and_show_commands(tmp_path: Path, capsys) -> None:
    _seed_repository(tmp_path)
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text(
        '{"name":"fixture-dashboard","dependencies":{"react":"latest"}}',
        encoding="utf-8",
    )
    (tmp_path / "frontend" / "pnpm-lock.yaml").write_text("", encoding="utf-8")

    build_exit = main(
        [
            "repo",
            "topology",
            "build",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    build_payload = json.loads(capsys.readouterr().out)

    status_exit = main(
        [
            "repo",
            "topology",
            "status",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    status_payload = json.loads(capsys.readouterr().out)

    show_exit = main(
        [
            "repo",
            "topology",
            "show",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    show_payload = json.loads(capsys.readouterr().out)

    assert build_exit == 0
    assert build_payload["freshness"] == "fresh"
    assert {component["component_id"] for component in build_payload["components"]} >= {
        "package:fixture",
        "app:fixture-dashboard",
    }
    assert status_exit == 0
    assert status_payload["freshness"] == "fresh"
    assert status_payload["recommendation_posture"] == "fresh"
    assert status_payload["component_count"] == len(build_payload["components"])
    assert show_exit == 0
    assert show_payload["dependencies"][0]["external_name"] == "react"


def test_repo_refresh_builds_index_and_topology(tmp_path: Path, capsys) -> None:
    _seed_repository(tmp_path)

    refresh_exit = main(
        [
            "repo",
            "refresh",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    refresh_payload = json.loads(capsys.readouterr().out)

    assert refresh_exit == 0
    assert refresh_payload["index"]["status"] == "fresh"
    assert refresh_payload["topology"]["freshness"] == "fresh"
    assert {
        component["component_id"]
        for component in refresh_payload["topology"]["components"]
    } >= {
        "package:fixture",
    }


def test_repo_refresh_queues_background_job(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            )
        )
    finally:
        connection.close()

    refresh_exit = main(
        [
            "repo",
            "refresh",
            "--background",
            "--session",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    refresh_payload = json.loads(capsys.readouterr().out)

    assert refresh_exit == 0
    assert refresh_payload["state"] == "queued"
    assert refresh_payload["kind"] == "derived_index"
    assert refresh_payload["job_type"] == "repository-intelligence-refresh"
    assert refresh_payload["payload"]["index_path"].endswith(
        ".glassbox/repository-index.json"
    )
    assert refresh_payload["payload"]["topology_path"].endswith(
        ".glassbox/workspace-topology.json"
    )


def test_repo_memory_candidates_requires_session_guidance(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "repo",
            "memory-candidates",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "repo memory-candidates requires --session SESSION_ID" in captured.err
    assert "glassbox session list --json --cwd ." in captured.err


def test_repo_intelligence_workflow_commands(tmp_path: Path, capsys) -> None:
    _seed_repository(tmp_path)
    assert main(["repo", "refresh", "--cwd", str(tmp_path)]) == 0
    capsys.readouterr()

    status_exit = main(["repo", "status", "--cwd", str(tmp_path), "--json"])
    status_payload = json.loads(capsys.readouterr().out)

    recipes_exit = main(["repo", "recipes", "list", "--cwd", str(tmp_path), "--json"])
    recipes_payload = json.loads(capsys.readouterr().out)
    recipe_id = recipes_payload[0]["recipe_id"]

    recipe_show_exit = main(
        ["repo", "recipes", "show", recipe_id, "--cwd", str(tmp_path), "--json"]
    )
    recipe_show_payload = json.loads(capsys.readouterr().out)

    subsystems_exit = main(
        ["repo", "subsystem", "list", "--cwd", str(tmp_path), "--json"]
    )
    subsystems_payload = json.loads(capsys.readouterr().out)
    subsystem_id = subsystems_payload[0]["subsystem_id"]

    subsystem_show_exit = main(
        [
            "repo",
            "subsystem",
            "show",
            subsystem_id,
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    subsystem_show_payload = json.loads(capsys.readouterr().out)

    path_exit = main(
        ["repo", "path", "src/sample.py", "--cwd", str(tmp_path), "--json"]
    )
    path_payload = json.loads(capsys.readouterr().out)

    recommend_exit = main(
        ["repo", "recommend", "src/sample.py", "--cwd", str(tmp_path), "--json"]
    )
    recommend_payload = json.loads(capsys.readouterr().out)

    stale_exit = main(["repo", "stale", "--cwd", str(tmp_path), "--json"])
    stale_payload = json.loads(capsys.readouterr().out)

    assert status_exit == 0
    assert status_payload["index"]["status"] == "fresh"
    assert status_payload["topology"]["freshness"] == "fresh"
    assert "glassbox repo refresh" in status_payload["next_actions"][-1]
    assert recipes_exit == 0
    assert recipe_show_exit == 0
    assert recipe_show_payload["recipe_id"] == recipe_id
    assert subsystems_exit == 0
    assert subsystem_show_exit == 0
    assert subsystem_show_payload["subsystem_id"] == subsystem_id
    assert path_exit == 0
    assert path_payload["path"] == "src/sample.py"
    assert path_payload["command_recipes"]
    assert recommend_exit == 0
    assert recommend_payload["status"] == "unavailable"
    assert "eval profile manifest" in recommend_payload["detail"]
    assert stale_exit == 0
    assert any(cue["state"] == "missing" for cue in stale_payload["cues"])
    assert any(
        "glassbox repo refresh" in action for action in stale_payload["next_actions"]
    )


def test_repo_index_status_human_output_explains_stale_snapshot(
    tmp_path: Path,
    capsys,
) -> None:
    _seed_repository(tmp_path)
    assert (
        main(
            [
                "repo",
                "index",
                "build",
                "--cwd",
                str(tmp_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    (tmp_path / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n\ndef changed() -> None:\n    pass\n",
        encoding="utf-8",
    )

    status_exit = main(
        [
            "repo",
            "index",
            "status",
            "--cwd",
            str(tmp_path),
        ]
    )
    output = capsys.readouterr().out

    assert status_exit == 0
    assert "Repository index: stale" in output
    assert "Reason: Current source digest differs" in output
    assert "Source diff:" in output
    assert "Changed sample: src/sample.py" in output
    assert f"- glassbox repo index build --cwd {tmp_path.resolve()}" in output


def _seed_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n[project.scripts]\nfixture = "sample:main"\n',
        encoding="utf-8",
    )
