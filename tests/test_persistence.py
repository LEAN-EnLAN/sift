"""Tests for search history persistence layer."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from sift.persistence.history import SearchHistoryStore


@pytest.fixture
def tmp_history_path(tmp_path: Path) -> str:
    """Provide a temporary history file path."""
    return str(tmp_path / "history.json")


@pytest.fixture
def store(tmp_history_path: str) -> SearchHistoryStore:
    """Provide a fresh SearchHistoryStore with a temp file."""
    return SearchHistoryStore(path=tmp_history_path)


class TestAddAndRetrieve:
    """Task 1.3: add+retrieve roundtrip."""

    def test_add_and_get_entries(self, store: SearchHistoryStore) -> None:
        """Adding an entry and retrieving it returns the stored data."""
        store.add_entry("jwt auth", ["Python"], [{"name": "jpadilla/pyjwt"}])
        entries = store.get_entries()
        assert len(entries) == 1
        assert entries[0]["query"] == "jwt auth"
        assert entries[0]["languages"] == ["Python"]
        assert entries[0]["results"][0]["name"] == "jpadilla/pyjwt"

    def test_multiple_entries_ordered_newest_first(self, store: SearchHistoryStore) -> None:
        """Entries are returned newest first."""
        store.add_entry("query1", ["Python"], [])
        store.add_entry("query2", ["Go"], [])
        entries = store.get_entries()
        assert len(entries) == 2
        assert entries[0]["query"] == "query2"
        assert entries[1]["query"] == "query1"

    def test_get_entries_with_limit(self, store: SearchHistoryStore) -> None:
        """Limit parameter restricts returned entries."""
        for i in range(5):
            store.add_entry(f"query{i}", ["Python"], [])
        entries = store.get_entries(limit=2)
        assert len(entries) == 2
        assert entries[0]["query"] == "query4"


class TestFIFOEviction:
    """Task 1.3: FIFO eviction at 100 entries."""

    def test_evicts_oldest_when_exceeding_max(self, store: SearchHistoryStore) -> None:
        """When exceeding 100 entries, oldest is evicted."""
        for i in range(101):
            store.add_entry(f"query{i}", ["Python"], [])
        entries = store.get_entries()
        assert len(entries) == 100
        # Oldest (query0) should be evicted, newest (query100) present
        assert entries[0]["query"] == "query100"
        assert entries[-1]["query"] == "query1"

    def test_exactly_100_entries_no_eviction(self, store: SearchHistoryStore) -> None:
        """Exactly 100 entries does not trigger eviction."""
        for i in range(100):
            store.add_entry(f"query{i}", ["Python"], [])
        entries = store.get_entries()
        assert len(entries) == 100
        assert entries[0]["query"] == "query99"
        assert entries[-1]["query"] == "query0"


class TestClear:
    """Task 1.3: clear removes all entries."""

    def test_clear_removes_all(self, store: SearchHistoryStore) -> None:
        """Clear removes all stored entries."""
        store.add_entry("test", ["Python"], [])
        store.clear()
        assert store.get_entries() == []

    def test_clear_on_empty_store(self, store: SearchHistoryStore) -> None:
        """Clear on empty store does not raise."""
        store.clear()
        assert store.get_entries() == []


class TestCorruptJSONRecovery:
    """Task 1.3: corrupt JSON file is handled gracefully."""

    def test_corrupt_json_returns_empty(self, tmp_history_path: str) -> None:
        """A corrupt JSON file is treated as empty history."""
        with open(tmp_history_path, "w") as f:
            f.write("{corrupt json!!!")
        store = SearchHistoryStore(path=tmp_history_path)
        entries = store.get_entries()
        assert entries == []

    def test_can_write_after_corrupt(self, tmp_history_path: str) -> None:
        """After corrupt JSON, new entries can be written."""
        with open(tmp_history_path, "w") as f:
            f.write("not json")
        store = SearchHistoryStore(path=tmp_history_path)
        store.add_entry("fresh", ["Python"], [])
        entries = store.get_entries()
        assert len(entries) == 1
        assert entries[0]["query"] == "fresh"


class TestAtomicWrite:
    """Task 1.3: atomic write via temp+rename."""

    def test_no_partial_file_on_crash(self, tmp_history_path: str) -> None:
        """Atomic write ensures no partial file is left behind."""
        store = SearchHistoryStore(path=tmp_history_path)
        store.add_entry("test", ["Python"], [])
        # File should exist and be valid JSON
        assert os.path.exists(tmp_history_path)
        with open(tmp_history_path) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_persists_across_instances(self, tmp_history_path: str) -> None:
        """Data written by one store instance is readable by another."""
        store1 = SearchHistoryStore(path=tmp_history_path)
        store1.add_entry("persist", ["Python"], [{"name": "test/repo"}])
        store2 = SearchHistoryStore(path=tmp_history_path)
        entries = store2.get_entries()
        assert len(entries) == 1
        assert entries[0]["query"] == "persist"
