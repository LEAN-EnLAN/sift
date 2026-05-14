"""Search history persistence backed by a local JSON file."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

_MAX_ENTRIES = 100


class SearchHistoryStore:
    """Persist recent searches to a local JSON file with atomic writes.

    Entries are stored newest-first with FIFO eviction when the limit is reached.
    """

    def __init__(self, path: str | None = None) -> None:
        self._path = path or str(Path.home() / ".cache" / "sift" / "history.json")

    def add_entry(
        self,
        query: str,
        languages: list[str],
        results: list[dict[str, Any]],
    ) -> None:
        """Add a search entry to history."""
        entries = self._load()
        entry = {
            "query": query,
            "languages": languages,
            "results": results,
        }
        entries.insert(0, entry)
        if len(entries) > _MAX_ENTRIES:
            entries = entries[:_MAX_ENTRIES]
        self._save(entries)

    def get_entries(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return history entries, newest first."""
        entries = self._load()
        if limit is not None:
            return entries[:limit]
        return entries

    def clear(self) -> None:
        """Remove all stored entries."""
        self._save([])

    def _load(self) -> list[dict[str, Any]]:
        """Load entries from disk, returning empty list on any error."""
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except (OSError, json.JSONDecodeError, ValueError):
            return []

    def _save(self, entries: list[dict[str, Any]]) -> None:
        """Atomically write entries to disk via temp file + rename."""
        dir_name = os.path.dirname(self._path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
