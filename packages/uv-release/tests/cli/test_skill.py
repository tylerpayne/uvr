from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import diny
import pytest

from conftest import run_cli


class TestSkillUpgrade:
    def test_scaffolds_skill_files(
        self, workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with diny.provide():
            run_cli("skill", "install")
        out = capsys.readouterr().out
        assert "Create" in out or "skill-upgrade" in out
        # Skill files should now exist in the workspace.
        skills_dir = workspace / ".claude" / "skills"
        assert skills_dir.exists()

    def test_print_template_with_existing_files(
        self, workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Scaffold first so skill files exist in cwd.
        with diny.provide():
            run_cli("skill", "install")
        assert (workspace / ".claude" / "skills").exists()
        capsys.readouterr()
        # --print-template must short-circuit even when files exist and no
        # --upgrade/--force flag is passed. The buggy provider previously
        # raised "Skill files already exist..." breaking the uvx fetch path.
        with diny.provide():
            run_cli("skill", "install", "--print-template")
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload, "expected at least one bundled skill"
        for files in payload.values():
            assert files and "rel_path" in files[0] and "content" in files[0]

    def test_upgrade_falls_back_when_skill_version_missing(
        self, workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Scaffold so skill files exist; the scaffold path records
        # skill-version in pyproject.toml.
        with diny.provide():
            run_cli("skill", "install")
        # Strip skill-version to simulate a user whose skills predate
        # version tracking (uv-release < 0.32.2).
        import tomlkit

        pp_path = workspace / "pyproject.toml"
        doc = tomlkit.loads(pp_path.read_text())
        doc["tool"]["uvr"]["config"].pop("skill-version", None)  # type: ignore[union-attr,index]
        pp_path.write_text(tomlkit.dumps(doc))
        capsys.readouterr()

        # Mock subprocess so the fetch fails fast — we only care about the
        # planning output (warning + fetch label), not network behavior.
        def _mock(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, stderr="mocked")

        # The mocked fetch fails, which causes execute_job to call
        # sys.exit(1). We only care that the planning output (warning +
        # fetch label) ran first, so swallow the SystemExit.
        with patch("subprocess.run", side_effect=_mock):
            with pytest.raises(SystemExit):
                with diny.provide():
                    run_cli("skill", "install", "--upgrade")

        out = capsys.readouterr().out
        assert "No skill-version recorded" in out, (
            f"expected fallback warning, got:\n{out}"
        )
        # The default fallback is 0.32.0 (oldest skills release).
        assert "uv-release 0.32.0" in out, (
            f"expected 0.32.0 baseline in output, got:\n{out}"
        )

    def test_upgrade_respects_from_version_override(
        self, workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Scaffold so files exist, then drop skill-version so the override
        # path is exercised cleanly (no recorded version to clash with).
        with diny.provide():
            run_cli("skill", "install")
        import tomlkit

        pp_path = workspace / "pyproject.toml"
        doc = tomlkit.loads(pp_path.read_text())
        doc["tool"]["uvr"]["config"].pop("skill-version", None)  # type: ignore[union-attr,index]
        pp_path.write_text(tomlkit.dumps(doc))
        capsys.readouterr()

        def _mock(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, stderr="mocked")

        with patch("subprocess.run", side_effect=_mock):
            with pytest.raises(SystemExit):
                with diny.provide():
                    run_cli("skill", "install", "--upgrade", "--from-version", "0.34.1")

        out = capsys.readouterr().out
        # --from-version wins over both the recorded value and the fallback.
        # No warning should fire since the user told us the version.
        assert "No skill-version recorded" not in out, (
            f"--from-version should suppress the fallback warning, got:\n{out}"
        )
        assert "uv-release 0.34.1" in out, (
            f"expected --from-version baseline in output, got:\n{out}"
        )
