"""Migration tests for sift rename — backward compat and _meta keys.

These tests verify that the rename preserves backward compatibility:
1. load_token() checks old ~/.config/repo-scout/ path and migrates on read
2. _meta envelope contains both sift_version and repo_scout_version
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestConfigMigration:
    """Task 1.11: load_token backward-compat fallback to old config path."""

    def test_load_token_checks_repo_scout_path_as_fallback(self) -> None:
        """load_token reads from old ~/.config/repo-scout/ when new path is empty."""
        from sift.auth import load_token

        with tempfile.TemporaryDirectory() as tmp:
            old_dir = Path(tmp) / ".config" / "repo-scout"
            old_dir.mkdir(parents=True)
            old_cfg = old_dir / "config.json"
            old_cfg.write_text(json.dumps({"github_token": "gho_oldpath_token"}), encoding="utf-8")

            # Create new dir so save_token migration doesn't fail on parent dir.
            new_dir = Path(tmp) / ".config" / "sift"
            new_dir.mkdir(parents=True, exist_ok=True)
            with (
                patch("sift.auth.config_path", return_value=new_dir / "config.json"),
                patch("sift.auth._old_config_path", return_value=old_dir / "config.json"),
            ):
                # Old path should be checked and migrated
                token = load_token()

        assert token == "gho_oldpath_token", (
            f"Expected token from old path, got: {token!r}"
        )

    def test_new_config_takes_priority_over_old(self) -> None:
        """When new sift config exists, it takes priority."""
        from sift.auth import load_token

        with tempfile.TemporaryDirectory() as tmp:
            # Old path has a token
            old_dir = Path(tmp) / ".config" / "repo-scout"
            old_dir.mkdir(parents=True)
            (old_dir / "config.json").write_text(
                json.dumps({"github_token": "gho_old"}), encoding="utf-8"
            )

            # New path has a different token
            new_dir = Path(tmp) / ".config" / "sift"
            new_dir.mkdir(parents=True)
            (new_dir / "config.json").write_text(
                json.dumps({"github_token": "gho_new"}), encoding="utf-8"
            )

            with (
                patch("sift.auth.config_path", return_value=new_dir / "config.json"),
                patch("sift.auth._old_config_path", return_value=old_dir / "config.json"),
            ):
                token = load_token()

        assert token == "gho_new", (
            f"Expected new path token, got: {token!r}"
        )

    def test_no_config_files_returns_none(self) -> None:
        """When neither config exists, load_token returns None."""
        from sift.auth import load_token

        with tempfile.TemporaryDirectory() as tmp:
            new_dir = Path(tmp) / ".config" / "sift"
            old_dir = Path(tmp) / ".config" / "repo-scout"
            with (
                patch("sift.auth.config_path", return_value=new_dir / "config.json"),
                patch("sift.auth._old_config_path", return_value=old_dir / "config.json"),
            ):
                token = load_token()

        assert token is None


class TestMetaDualKeys:
    """Task 1.12: _meta envelope has both sift_version and repo_scout_version."""

    def test_meta_has_both_version_keys(self) -> None:
        """Agent JSON _meta includes sift_version AND repo_scout_version."""
        from sift.models import RepoCandidate
        from sift.render import render_agent_json

        repo = RepoCandidate(
            full_name="owner/repo",
            html_url="https://github.com/owner/repo",
            description="Test",
            language="Python",
            stars=100,
            forks=10,
            watchers=5,
            open_issues=1,
            pushed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            created_at="2023-01-01T00:00:00Z",
            archived=False,
            fork=False,
            license_spdx="MIT",
        )
        output = render_agent_json([repo], speed_tier="fast", query="test")
        data = json.loads(output)

        assert "sift_version" in data["_meta"], (
            "sift_version key missing from _meta"
        )
        assert "repo_scout_version" in data["_meta"], (
            "repo_scout_version key missing from _meta"
        )

    def test_both_versions_have_same_value(self) -> None:
        """Both version keys report the same version string."""
        from sift.models import RepoCandidate
        from sift.render import render_agent_json

        repo = RepoCandidate(
            full_name="owner/repo",
            html_url="https://github.com/owner/repo",
            description="Test",
            language="Python",
            stars=100,
            forks=10,
            watchers=5,
            open_issues=1,
            pushed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            created_at="2023-01-01T00:00:00Z",
            archived=False,
            fork=False,
            license_spdx="MIT",
        )
        output = render_agent_json([repo], speed_tier="fast", query="test")
        data = json.loads(output)

        assert data["_meta"]["sift_version"] == data["_meta"]["repo_scout_version"], (
            f"sift_version ({data['_meta']['sift_version']}) != "
            f"repo_scout_version ({data['_meta']['repo_scout_version']})"
        )
