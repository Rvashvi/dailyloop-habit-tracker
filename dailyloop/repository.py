"""Data layer: translates between :class:`Habit` objects and SQLite rows."""

import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from .database import DatabaseManager
from .exceptions import DuplicateHabitError, HabitNotFoundError
from .habit import Habit


class HabitRepository:
    """Stores and loads habits. Contains all SQL of the application."""

    def __init__(self, database: DatabaseManager) -> None:
        self._conn: sqlite3.Connection = database.connection

    def add(self, habit: Habit) -> None:
        """Insert a new habit (with any existing history) and set its id.

        Raises:
            DuplicateHabitError: if a habit with the same name already exists.
        """
        try:
            with self._conn:  # one transaction: commit on success, rollback on error
                cursor = self._conn.execute(
                    "INSERT INTO habit (name, task, periodicity, created_at) VALUES (?, ?, ?, ?)",
                    (habit.name, habit.task, habit.periodicity.value, habit.created_at.isoformat()),
                )
                habit_id = cursor.lastrowid
                self._conn.executemany(
                    "INSERT INTO completion (habit_id, completed_at) VALUES (?, ?)",
                    [(habit_id, ts.isoformat()) for ts in habit.history],
                )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc):
                raise DuplicateHabitError(
                    "A habit named {!r} already exists.".format(habit.name)
                ) from exc
            raise
        habit.habit_id = habit_id

    def remove(self, habit_id: int) -> None:
        """Delete a habit; its completions are removed by ``ON DELETE CASCADE``.

        Raises:
            HabitNotFoundError: if no habit has this id.
        """
        with self._conn:
            cursor = self._conn.execute("DELETE FROM habit WHERE id = ?", (habit_id,))
        if cursor.rowcount == 0:
            raise HabitNotFoundError("No habit with id {}.".format(habit_id))

    def add_completion(self, habit_id: int, at: datetime) -> None:
        """Store one check-off timestamp for an existing habit.

        Raises:
            HabitNotFoundError: if no habit has this id.
        """
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO completion (habit_id, completed_at) VALUES (?, ?)",
                    (habit_id, at.isoformat()),
                )
        except sqlite3.IntegrityError as exc:
            raise HabitNotFoundError("No habit with id {}.".format(habit_id)) from exc

    def fetch(self, habit_id: int) -> Habit:
        """Load one habit including its history.

        Raises:
            HabitNotFoundError: if no habit has this id.
        """
        row = self._conn.execute(
            "SELECT id, name, task, periodicity, created_at FROM habit WHERE id = ?",
            (habit_id,),
        ).fetchone()
        if row is None:
            raise HabitNotFoundError("No habit with id {}.".format(habit_id))
        timestamps = [
            datetime.fromisoformat(r["completed_at"])
            for r in self._conn.execute(
                "SELECT completed_at FROM completion WHERE habit_id = ? ORDER BY completed_at",
                (habit_id,),
            )
        ]
        return self._to_habit(row, timestamps)

    def fetch_all(self) -> List[Habit]:
        """Load all habits (ordered by id) with their histories, using two queries."""
        history: Dict[int, List[datetime]] = defaultdict(list)
        for r in self._conn.execute(
            "SELECT habit_id, completed_at FROM completion ORDER BY completed_at"
        ):
            history[r["habit_id"]].append(datetime.fromisoformat(r["completed_at"]))
        rows = self._conn.execute(
            "SELECT id, name, task, periodicity, created_at FROM habit ORDER BY id"
        ).fetchall()
        return [self._to_habit(row, history[row["id"]]) for row in rows]

    @staticmethod
    def _to_habit(row: sqlite3.Row, timestamps: List[datetime]) -> Habit:
        """Map a database row (plus its completions) to a :class:`Habit`."""
        return Habit(
            name=row["name"],
            task=row["task"],
            periodicity=row["periodicity"],
            created_at=datetime.fromisoformat(row["created_at"]),
            history=timestamps,
            habit_id=row["id"],
        )
