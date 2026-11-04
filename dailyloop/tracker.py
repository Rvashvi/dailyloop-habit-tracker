"""Service layer: the use cases of the application."""

from datetime import datetime
from typing import List, Optional, Union

from .habit import Habit, Periodicity
from .repository import HabitRepository


class HabitTracker:
    """Coordinates creating, completing and deleting habits.

    The tracker contains no SQL and no user interface code: it validates
    through the :class:`Habit` class and persists through the repository.
    """

    def __init__(self, repo: HabitRepository) -> None:
        self._repo = repo

    def create_habit(
        self,
        name: str,
        task: str,
        periodicity: Union[str, Periodicity],
        created_at: Optional[datetime] = None,
    ) -> Habit:
        """Create and store a new habit.

        Raises:
            InvalidHabitError: for an empty name/task or unknown periodicity.
            DuplicateHabitError: if the name is already used.
        """
        habit = Habit(name, task, Periodicity.parse(periodicity), created_at)
        self._repo.add(habit)
        return habit

    def delete_habit(self, habit_id: int) -> None:
        """Delete a habit and its history.

        Raises:
            HabitNotFoundError: if the id is unknown.
        """
        self._repo.remove(habit_id)

    def complete_habit(self, habit_id: int, at: Optional[datetime] = None) -> datetime:
        """Check off a habit at ``at`` (default: now), store it, return the timestamp.

        Raises:
            HabitNotFoundError: if the id is unknown.
            InvalidCheckOffError: if the timestamp is in the future or before creation.
        """
        habit = self._repo.fetch(habit_id)
        timestamp = habit.mark_done(at)  # validates; nothing is stored if it raises
        self._repo.add_completion(habit_id, timestamp)
        return timestamp

    def get_habit(self, habit_id: int) -> Habit:
        """Return one habit with its history."""
        return self._repo.fetch(habit_id)

    def get_all(self) -> List[Habit]:
        """Return all habits with their histories."""
        return self._repo.fetch_all()
