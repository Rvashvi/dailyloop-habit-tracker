"""Domain model: the :class:`Habit` class and the :class:`Periodicity` enum.

Streak logic is built on one idea: every timestamp is converted to an integer
*period index*. Consecutive periods have consecutive indices, so a streak is
simply a run of consecutive integers. This works across month and year
boundaries without special cases.
"""

from bisect import insort
from datetime import date, datetime
from enum import Enum
from typing import Iterable, List, Optional, Set, Union

from .exceptions import InvalidCheckOffError, InvalidHabitError


class Periodicity(Enum):
    """How often a habit has to be completed."""

    DAILY = "daily"
    WEEKLY = "weekly"

    @classmethod
    def parse(cls, value: Union[str, "Periodicity"]) -> "Periodicity":
        """Convert text such as ``"Daily"`` into a :class:`Periodicity`.

        Raises:
            InvalidHabitError: if the text is not a known periodicity.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            choices = ", ".join(p.value for p in cls)
            raise InvalidHabitError(
                "Unknown periodicity {!r}; choose one of: {}.".format(value, choices)
            ) from None

    @property
    def unit(self) -> str:
        """Singular name of one period (``"day"`` or ``"week"``)."""
        return "day" if self is Periodicity.DAILY else "week"

    def period_index(self, at: date) -> int:
        """Return the integer index of the period that contains ``at``.

        * daily habits: the proleptic Gregorian ordinal of the date
        * weekly habits: ``(ordinal - 1) // 7``. Ordinal 1 is a Monday, so
          weeks run from Monday to Sunday.

        Works for both :class:`~datetime.date` and :class:`~datetime.datetime`.
        """
        ordinal = at.toordinal()
        if self is Periodicity.WEEKLY:
            return (ordinal - 1) // 7
        return ordinal


class Habit:
    """A clearly defined task that has to be completed periodically.

    Args:
        name: Unique, human readable name (e.g. ``"Brush teeth"``).
        task: Task specification (e.g. ``"Brush teeth for two minutes"``).
        periodicity: :class:`Periodicity` or its text form (``"daily"``/``"weekly"``).
        created_at: When the habit was created. Defaults to now.
        history: Existing completion timestamps (used when loading from storage).
        habit_id: Database id, ``None`` until the habit has been stored.

    All timestamps are naive local date-times.
    """

    def __init__(
        self,
        name: str,
        task: str,
        periodicity: Union[str, Periodicity],
        created_at: Optional[datetime] = None,
        history: Optional[Iterable[datetime]] = None,
        habit_id: Optional[int] = None,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise InvalidHabitError("A habit needs a non-empty name.")
        if not isinstance(task, str) or not task.strip():
            raise InvalidHabitError("A habit needs a non-empty task description.")
        self._habit_id = habit_id
        self._name = name.strip()
        self._task = task.strip()
        self._periodicity = Periodicity.parse(periodicity)
        self._created_at = created_at if created_at is not None else datetime.now()
        self._history: List[datetime] = sorted(history) if history else []

    # ------------------------------------------------------------------ properties
    @property
    def habit_id(self) -> Optional[int]:
        """Database id, or ``None`` if the habit has not been stored yet."""
        return self._habit_id

    @habit_id.setter
    def habit_id(self, value: int) -> None:
        """Set the id once the repository has stored the habit."""
        self._habit_id = value

    @property
    def name(self) -> str:
        """Unique name of the habit."""
        return self._name

    @property
    def task(self) -> str:
        """Task specification."""
        return self._task

    @property
    def periodicity(self) -> Periodicity:
        """How often the task has to be completed."""
        return self._periodicity

    @property
    def created_at(self) -> datetime:
        """When the habit was created."""
        return self._created_at

    @property
    def history(self) -> List[datetime]:
        """All completion timestamps, oldest first (a copy, safe to modify)."""
        return list(self._history)

    # --------------------------------------------------------------------- behaviour
    def mark_done(self, at: Optional[datetime] = None) -> datetime:
        """Check off the task at ``at`` (default: now) and return the timestamp.

        A habit can be checked off any number of times. Several check-offs in
        the same period are all kept in the history but count as one completed
        period.

        Raises:
            InvalidCheckOffError: if ``at`` is in the future, before the habit
                was created, or timezone-aware.
        """
        now = datetime.now()
        at = now if at is None else at
        if at.tzinfo is not None:
            raise InvalidCheckOffError("Timezone-aware timestamps are not supported.")
        if at > now:
            raise InvalidCheckOffError(
                "Cannot check off a task in the future ({:%Y-%m-%d %H:%M}).".format(at)
            )
        if at < self._created_at:
            raise InvalidCheckOffError(
                "Cannot check off before the habit was created ({:%Y-%m-%d %H:%M}).".format(
                    self._created_at
                )
            )
        insort(self._history, at)
        return at

    def completed_periods(self) -> Set[int]:
        """Indices of all periods with at least one check-off."""
        return {self._periodicity.period_index(ts) for ts in self._history}

    def is_done(self, day: date) -> bool:
        """Whether the period containing ``day`` has been completed."""
        return self._periodicity.period_index(day) in self.completed_periods()

    def __repr__(self) -> str:
        return "Habit(id={!r}, name={!r}, periodicity={}, check-offs={})".format(
            self._habit_id, self._name, self._periodicity.value, len(self._history)
        )
