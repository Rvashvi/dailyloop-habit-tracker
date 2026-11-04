"""SQLite connection and schema management."""

import sqlite3
from typing import Union
from pathlib import Path

DEFAULT_DB_PATH = "habits.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS habit (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    task        TEXT NOT NULL,
    periodicity TEXT NOT NULL CHECK (periodicity IN ('daily', 'weekly')),
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS completion (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id     INTEGER NOT NULL REFERENCES habit(id) ON DELETE CASCADE,
    completed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_completion_habit
    ON completion (habit_id, completed_at);
"""


class DatabaseManager:
    """Owns the SQLite connection and makes sure the schema exists.

    Args:
        path: Database file, or ``":memory:"`` for a temporary database (tests).
    """

    def __init__(self, path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
        self._path = str(path)
        self._connection = sqlite3.connect(self._path)
        self._connection.row_factory = sqlite3.Row
        # SQLite ignores foreign keys unless this is switched on per connection.
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(SCHEMA)

    @property
    def path(self) -> str:
        """Location of the database file."""
        return self._path

    @property
    def connection(self) -> sqlite3.Connection:
        """The open :class:`sqlite3.Connection`."""
        return self._connection

    def close(self) -> None:
        """Close the connection."""
        self._connection.close()

    def __enter__(self) -> "DatabaseManager":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
