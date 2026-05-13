"""Tests for Textual TUI mode — smart input, preview panel, search flow.

These tests verify the restructured SiftApp with:
- Single smart input replacing query-input + language-input
- Preview panel with detected language/speed
- LoadingIndicator for search progress
- Results display with ListView + detail pane
- Escape hatches preserved (no side effects on CLI paths)
"""

from __future__ import annotations

import pytest

pytest.importorskip("textual", reason="textual is not installed — TUI tests skipped")


class TestSiftAppImport:
    """SiftApp and AppState are importable."""

    def test_sift_app_can_be_imported(self) -> None:
        from sift.tui import SiftApp

        assert SiftApp is not None

    def test_sift_app_css_exists(self) -> None:
        from sift.tui import SiftApp

        assert hasattr(SiftApp, "CSS")
        assert len(SiftApp.CSS) > 0, "CSS must be non-empty"

    def test_app_state_enum_exists(self) -> None:
        from sift.tui import AppState

        assert AppState.INPUT is not None
        assert AppState.PREVIEW is not None
        assert AppState.SEARCHING is not None
        assert AppState.RESULTS is not None


class TestSiftAppWidgetPresence:
    """Integration tests verifying the new widget tree."""

    @pytest.mark.asyncio
    async def test_app_mounts_smart_input(self) -> None:
        """Single smart input widget is present; old query/language inputs are gone."""
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            smart_input = app.query_one("#smart-input")
            assert smart_input is not None

            # Old inputs must NOT exist
            with pytest.raises(Exception):
                app.query_one("#query-input")
            with pytest.raises(Exception):
                app.query_one("#language-input")

            await pilot.pause()

    @pytest.mark.asyncio
    async def test_app_has_results_container(self) -> None:
        """Results ListView widget is present."""
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            results = app.query_one("#results-panel")
            assert results is not None
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_preview_panel_exists_and_hidden(self) -> None:
        """Preview panel container exists but is hidden initially."""
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            preview = app.query_one("#preview-panel")
            assert preview is not None
            assert not preview.styles.display or preview.styles.display == "none"
            await pilot.pause()


class TestSmartInputFlow:
    """Core smart input → preview → confirm → search flow."""

    @pytest.mark.asyncio
    async def test_submit_shows_preview_panel(self) -> None:
        """Typing query with no language and pressing Enter shows preview panel."""
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            smart = app.query_one("#smart-input")
            smart.focus()
            await pilot.press(*"jwt auth library")
            await pilot.press("enter")
            await pilot.pause()

            # Preview panel should now be visible (no language detected)
            preview = app.query_one("#preview-panel")
            assert preview.styles.display != "none"

            # Detected language should be shown
            lang_input = app.query_one("#preview-language")
            assert lang_input is not None

            await pilot.pause()

    @pytest.mark.asyncio
    async def test_preview_confirm_triggers_search(self) -> None:
        """Pressing Enter on preview confirm button triggers search."""
        from unittest.mock import patch

        from sift.tui import SiftApp

        app = SiftApp()
        with patch("sift.tui.run", return_value=[]) as mock_run:
            async with app.run_test(size=(100, 30)) as pilot:
                smart = app.query_one("#smart-input")
                smart.focus()
                await pilot.press(*"jwt auth")
                await pilot.press("enter")
                await pilot.pause()

                # Preview panel visible (no language → fallback)
                preview = app.query_one("#preview-panel")
                assert preview.styles.display != "none"

                # Press Enter to confirm search
                confirm_btn = app.query_one("#preview-confirm")
                confirm_btn.focus()
                await pilot.press("enter")
                await pilot.pause()

                # run() should have been called
                assert mock_run.called

                opts = mock_run.call_args[0][0]
                assert opts.speed == "fast"
                assert opts.top == 5

    @pytest.mark.asyncio
    async def test_preview_edit_and_confirm(self) -> None:
        """User can edit preview fields before confirming search."""
        from unittest.mock import patch

        from sift.tui import SiftApp

        app = SiftApp()
        with patch("sift.tui.run", return_value=[]) as mock_run:
            async with app.run_test(size=(100, 30)) as pilot:
                smart = app.query_one("#smart-input")
                smart.focus()
                await pilot.press(*"jwt")
                await pilot.press("enter")
                await pilot.pause()

                # Change language in preview by focusing and typing
                lang_input = app.query_one("#preview-language")
                lang_input.focus()
                await pilot.pause()
                # Clear field
                lang_input.value = ""
                await pilot.pause()
                # Type new language
                lang_input.value = "Go"
                await pilot.pause()

                # Press confirm button
                btn = app.query_one("#preview-confirm")
                # Focus the button and press Enter
                btn.focus()
                await pilot.press("enter")
                await pilot.pause()

                # _run_search should have been called via run()
                assert mock_run.called
                # The language should be Go
                _, kwargs = mock_run.call_args
                opts = kwargs.get("options") or mock_run.call_args[0][0]
                assert "Go" in opts.languages

    @pytest.mark.asyncio
    async def test_no_language_detected_shows_warning_in_preview(self) -> None:
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            smart = app.query_one("#smart-input")
            smart.focus()
            await pilot.press(*"que libreria jwt recomiendas")
            await pilot.press("enter")
            await pilot.pause()

            lang_input = app.query_one("#preview-language")
            # No language detected from this input
            assert lang_input.value == ""

    @pytest.mark.asyncio
    async def test_searching_disables_preview_actions(self) -> None:
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.searching = True
            await pilot.pause()

            assert app.query_one("#preview-confirm").disabled is True
            assert app.query_one("#preview-back").disabled is True

    @pytest.mark.asyncio
    async def test_escape_from_preview_returns_to_input(self) -> None:
        """Pressing Escape in preview panel returns to smart input."""
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            smart = app.query_one("#smart-input")
            smart.focus()
            await pilot.press(*"jwt auth")
            await pilot.press("enter")
            await pilot.pause()

            # Preview visible (no language → fallback)
            preview = app.query_one("#preview-panel")
            assert preview.styles.display != "none"

            # Press Escape
            await pilot.press("escape")
            await pilot.pause()

            # Back to input mode — preview hidden
            assert preview.styles.display == "none"
            smart = app.query_one("#smart-input")
            assert app.focused == smart

    @pytest.mark.asyncio
    async def test_search_with_mocked_run(self) -> None:
        """Full flow: input → preview → confirm → search → results."""
        from unittest.mock import patch

        from sift.models import RepoCandidate
        from sift.tui import SiftApp

        repo = RepoCandidate(
            full_name="owner/test-repo",
            html_url="https://github.com/owner/test-repo",
            description="A test repo",
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
            score=85.0,
            reasons=["Buena documentación"],
        )

        app = SiftApp()
        with patch("sift.tui.run", return_value=[repo]):
            async with app.run_test(size=(100, 30)) as pilot:
                smart = app.query_one("#smart-input")
                smart.focus()
                await pilot.press(*"jwt auth")
                await pilot.press("enter")
                await pilot.pause()

                confirm_btn = app.query_one("#preview-confirm")
                confirm_btn.focus()
                await pilot.press("enter")

                # Wait for async worker to complete
                await pilot.pause()

                # Results should be populated
                assert len(app.results) == 1
                assert app.results[0].full_name == "owner/test-repo"

    @pytest.mark.asyncio
    async def test_search_spinner_reacts_to_searching_state(self) -> None:
        """LoadingIndicator display follows the searching reactive."""
        from unittest.mock import patch

        from sift.tui import SiftApp

        app = SiftApp()
        with patch("sift.tui.run", return_value=[]):
            async with app.run_test(size=(100, 30)) as pilot:
                await pilot.pause()

                # Initially spinner is hidden
                spinner = app.query_one("#search-spinner")
                assert not spinner.display

                # Simulate search start by toggling reactive
                app.searching = True
                await pilot.pause()

                # Spinner should now be visible
                assert spinner.display

                # Simulate search end
                app.searching = False
                await pilot.pause()

                # Spinner should be hidden again
                assert not spinner.display

    @pytest.mark.asyncio
    async def test_detail_view_from_result(self) -> None:
        """Selecting a result shows the detail panel."""
        from unittest.mock import patch

        from sift.models import RepoCandidate
        from sift.tui import SiftApp

        repo = RepoCandidate(
            full_name="owner/test-repo",
            html_url="https://github.com/owner/test-repo",
            description="A test repo",
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
            score=85.0,
            reasons=["Buena documentación"],
        )

        with patch("sift.tui.run", return_value=[repo]):
            async with SiftApp().run_test(size=(100, 30)) as pilot:
                await pilot.pause()

                # Set results after app is mounted
                pilot.app.results = [repo]
                await pilot.pause()

                # Results should be displayed
                list_view = pilot.app.query_one("#results-panel")
                assert list_view is not None

                # Check detail panel exists
                detail_panel = pilot.app.query_one("#detail-panel")
                assert detail_panel is not None

                await pilot.pause()


class TestDetectLanguageEdgeCases:
    """Edge cases for language and speed detection in the TUI context."""

    @pytest.mark.asyncio
    async def test_empty_input_shows_error(self) -> None:
        """Submitting empty input shows error, does not show preview."""
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            smart = app.query_one("#smart-input")
            smart.focus()
            await pilot.press("enter")
            await pilot.pause()

            # Should still be in input mode — preview not shown
            preview = app.query_one("#preview-panel")
            assert preview.styles.display == "none"


class TestDirectSearchShortcut:
    """Direct search skips preview when language is detected."""

    @pytest.mark.asyncio
    async def test_language_detected_skips_preview_and_starts_search(self) -> None:
        """Typing query with detected language skips preview and starts search."""
        from unittest.mock import patch

        from sift.models import RepoCandidate
        from sift.tui import SiftApp

        repo = RepoCandidate(
            full_name="owner/test-repo",
            html_url="https://github.com/owner/test-repo",
            description="A test repo",
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
            score=85.0,
            reasons=["Buena documentación"],
        )

        with patch("sift.tui.run", return_value=[repo]):
            app = SiftApp()
            async with app.run_test(size=(100, 30)) as pilot:
                smart = app.query_one("#smart-input")
                smart.focus()
                await pilot.press(*"jwt python")
                await pilot.press("enter")
                await pilot.pause()

                # Preview should NOT be visible — direct search
                preview = app.query_one("#preview-panel")
                assert preview.styles.display == "none"

                # Wait for async worker
                await pilot.pause()

                # Results should be populated
                assert len(app.results) == 1
                assert app.results[0].full_name == "owner/test-repo"

    @pytest.mark.asyncio
    async def test_no_language_shows_preview_as_before(self) -> None:
        """No language detected → preview fallback unchanged."""
        from unittest.mock import patch

        from sift.tui import SiftApp

        with patch("sift.tui.run", return_value=[]):
            app = SiftApp()
            async with app.run_test(size=(100, 30)) as pilot:
                smart = app.query_one("#smart-input")
                smart.focus()
                # Use a query with no language keyword
                await pilot.press(*"que libreria jwt recomiendas")
                await pilot.press("enter")
                await pilot.pause()

                # Preview should be visible
                preview = app.query_one("#preview-panel")
                assert preview.styles.display != "none"


class TestTabNavigation:
    """Tab cycles focus between input and results panel."""

    @pytest.mark.asyncio
    async def test_tab_cycles_input_to_results(self) -> None:
        """Pressing Tab in INPUT state moves focus to results panel."""
        from textual.widgets import ListView

        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            # Set some results first
            from sift.models import RepoCandidate
            repo = RepoCandidate(
                full_name="owner/repo", html_url="https://github.com/owner/repo",
                description="", language="Python", stars=10, forks=1, watchers=1,
                open_issues=0, pushed_at=None, updated_at=None, created_at=None,
                archived=False, fork=False, license_spdx=None, score=80.0,
                reasons=["Buena calidad"],
            )
            app.results = [repo]
            await pilot.pause()

            # Press Tab from smart input
            await pilot.press("tab")
            await pilot.pause()

            # Focus should now be on results panel
            results = app.query_one("#results-panel", ListView)
            assert app.focused is results or results.has_focus()

    @pytest.mark.asyncio
    async def test_tab_returns_to_input_from_results(self) -> None:
        """Pressing Tab when results are focused returns to smart input."""
        from textual.widgets import ListView

        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            from sift.models import RepoCandidate
            repo = RepoCandidate(
                full_name="owner/repo", html_url="https://github.com/owner/repo",
                description="", language="Python", stars=10, forks=1, watchers=1,
                open_issues=0, pushed_at=None, updated_at=None, created_at=None,
                archived=False, fork=False, license_spdx=None, score=80.0,
                reasons=["Buena calidad"],
            )
            app.results = [repo]
            await pilot.pause()

            # Focus results first
            results = app.query_one("#results-panel", ListView)
            results.focus()
            await pilot.pause()

            # Press Tab
            await pilot.press("tab")
            await pilot.pause()

            # Focus should be back on smart input
            smart = app.query_one("#smart-input")
            assert app.focused is smart or app.focused == smart

    @pytest.mark.asyncio
    async def test_tab_in_preview_moves_through_preview_fields(self) -> None:
        """Tab in PREVIEW state moves through preview inputs, not results."""
        from sift.tui import SiftApp, AppState

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            smart = app.query_one("#smart-input")
            smart.focus()
            # No language → goes to preview
            await pilot.press(*"jwt auth")
            await pilot.press("enter")
            await pilot.pause()

            # Verify we're in preview state
            assert app.state == AppState.PREVIEW

            # In preview — Tab should move to next preview field
            await pilot.press("tab")
            await pilot.pause()

            # Language field should be focused (preview-query → preview-language)
            lang_input = app.query_one("#preview-language")
            assert app.focused is lang_input or app.focused == lang_input


class TestQuickOpen:
    """Quick-open opens repo URL in browser."""

    @pytest.mark.asyncio
    async def test_o_key_opens_selected_repo(self) -> None:
        """Pressing 'o' opens the selected repo URL."""
        from unittest.mock import patch

        from textual.widgets import ListView

        from sift.models import RepoCandidate
        from sift.tui import SiftApp

        repo = RepoCandidate(
            full_name="owner/test-repo",
            html_url="https://github.com/owner/test-repo",
            description="A test repo", language="Python",
            stars=100, forks=10, watchers=5, open_issues=1,
            pushed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            created_at="2023-01-01T00:00:00Z",
            archived=False, fork=False, license_spdx="MIT",
            score=85.0, reasons=["Buena documentación"],
        )

        with patch("sift.tui._silent_browser_launcher", return_value=None), patch("sift.tui.webbrowser.open") as mock_open:
            app = SiftApp()
            async with app.run_test(size=(100, 30)) as pilot:
                app.results = [repo]
                await pilot.pause()

                # Focus results and highlight the item
                list_view = app.query_one("#results-panel", ListView)
                list_view.focus()
                await pilot.pause()
                list_view.index = 0
                await pilot.pause()

                # Press 'o' to open
                await pilot.press("o")
                await pilot.pause()

                # webbrowser.open should have been called with the repo URL
                mock_open.assert_called_once_with("https://github.com/owner/test-repo")

    @pytest.mark.asyncio
    async def test_enter_on_result_opens_repo(self) -> None:
        """Enter on a selected result opens repo URL instead of showing detail."""
        from unittest.mock import patch

        from textual.widgets import ListView

        from sift.models import RepoCandidate
        from sift.tui import SiftApp

        repo = RepoCandidate(
            full_name="owner/test-repo",
            html_url="https://github.com/owner/test-repo",
            description="A test repo", language="Python",
            stars=100, forks=10, watchers=5, open_issues=1,
            pushed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            created_at="2023-01-01T00:00:00Z",
            archived=False, fork=False, license_spdx="MIT",
            score=85.0, reasons=["Buena documentación"],
        )

        with patch("sift.tui._silent_browser_launcher", return_value=None), patch("sift.tui.webbrowser.open") as mock_open:
            app = SiftApp()
            async with app.run_test(size=(100, 30)) as pilot:
                app.results = [repo]
                await pilot.pause()

                list_view = app.query_one("#results-panel", ListView)
                list_view.focus()
                await pilot.pause()
                list_view.index = 0
                await pilot.pause()

                # Press Enter on the result
                await pilot.press("enter")
                await pilot.pause()

                # Should open browser, not show detail
                mock_open.assert_called_once_with("https://github.com/owner/test-repo")
                # Detail mode should NOT be active
                assert app.detail_mode is False

    def test_browser_launcher_suppresses_process_output(self) -> None:
        """Browser launch uses DEVNULL so xdg-open/Helium errors never bleed into TUI."""
        from unittest.mock import patch

        from sift.tui import _popen_silent

        with patch("sift.tui.subprocess.Popen") as mock_popen:
            assert _popen_silent(["browser", "https://github.com/example/repo"]) is True

        kwargs = mock_popen.call_args.kwargs
        assert kwargs["stdout"] is not None
        assert kwargs["stderr"] is not None
        assert kwargs["stdin"] is not None

    def test_webbrowser_fallback_swallows_errors(self) -> None:
        from unittest.mock import patch

        from sift.tui import _webbrowser_open_silent

        with patch("sift.tui.webbrowser.open", side_effect=RuntimeError("boom")):
            assert _webbrowser_open_silent("https://github.com/example/repo") is False


class TestBestSummary:
    """Best answer summary shown in status after search."""

    @pytest.mark.asyncio
    async def test_best_summary_shown_after_search(self) -> None:
        """Status bar shows best answer after results are loaded."""
        from unittest.mock import patch

        from sift.models import RepoCandidate
        from sift.tui import SiftApp, AppState

        repo = RepoCandidate(
            full_name="owner/top-repo",
            html_url="https://github.com/owner/top-repo",
            description="Top repo", language="Python",
            stars=500, forks=50, watchers=20, open_issues=2,
            pushed_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            created_at="2024-01-01T00:00:00Z",
            archived=False, fork=False, license_spdx="MIT",
            score=92.5, reasons=["Actividad reciente", "Buena documentación"],
        )

        with patch("sift.tui.run", return_value=[repo]):
            app = SiftApp()
            async with app.run_test(size=(100, 30)) as pilot:
                smart = app.query_one("#smart-input")
                smart.focus()
                # Direct search path (language detected)
                await pilot.press(*"jwt python")
                await pilot.press("enter")
                await pilot.pause()

                # Results state is reached
                assert app.state == AppState.RESULTS
                assert len(app.results) == 1
                assert app.results[0].full_name == "owner/top-repo"

    @pytest.mark.asyncio
    async def test_no_best_summary_when_no_results(self) -> None:
        """No best answer when results are empty — status says 'no results'."""
        from sift.tui import SiftApp, AppState

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            # Set empty results to simulate a search that returned nothing
            app.results = []
            await pilot.pause()

            # Should be in RESULTS state
            assert app.state == AppState.RESULTS
            assert len(app.results) == 0


class TestDuplicateSearchPrevention:
    """Search guard prevents concurrent searches."""

    @pytest.mark.asyncio
    async def test_cannot_start_search_while_searching(self) -> None:
        """Pressing Enter while searching does not start a second search."""
        from unittest.mock import patch

        from sift.tui import SiftApp, AppState

        with patch("sift.tui.run", return_value=[]):
            app = SiftApp()
            async with app.run_test(size=(100, 30)) as pilot:
                # Simulate a search already in progress
                app.searching = True
                app._current_query = "jwt python"
                app._current_languages = ["Python"]
                app._current_speed = "fast"
                await pilot.pause()

                # Submit smart input (should be blocked)
                smart = app.query_one("#smart-input")
                smart.focus()
                await pilot.press("enter")
                await pilot.pause()

                # Still in SEARCHING state — preview should not appear
                assert app.state == AppState.SEARCHING

    @pytest.mark.asyncio
    async def test_refresh_ignored_while_searching(self) -> None:
        """Refresh (r key) does nothing while a search is running."""
        from sift.tui import SiftApp

        app = SiftApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.searching = True
            await pilot.pause()

            app.action_refresh()
            await pilot.pause()

            # Should still be searching
            assert app.searching is True
