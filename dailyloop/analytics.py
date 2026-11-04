"""Analytics module, written in the functional programming paradigm.

Every function is *pure*: it only reads the habits it is given, never changes
them, and returns a new value. They are built from ``map``, ``filter``,
``sorted``, ``functools.reduce`` and ``itertools``, and can be tested in
isolation without a database.
"""

from datetime import date
from functools import reduce
from itertools import count, groupby, takewhile
from typing import Iterable, List, NamedTuple, Optional, Tuple

from .habit import Habit, Periodicity


class Difficulty(NamedTuple):
    """How many periods of a habit were missed within a time window."""

    habit: Habit
    missed: int
    total: int

    @property
    def miss_rate(self) -> float:
        """Share of missed periods between 0.0 and 1.0."""
        return self.missed / self.total if self.total else 0.0


def list_habits(habits: Iterable[Habit]) -> List[Habit]:
    """Return a new list of all tracked habits, ordered by id."""
    return sorted(habits, key=lambda h: (h.habit_id is None, h.habit_id or 0))


def select_by_periodicity(habits: Iterable[Habit], periodicity: Periodicity) -> List[Habit]:
    """Return all habits that have the given periodicity (daily or weekly)."""
    return list(filter(lambda h: h.periodicity is periodicity, habits))


def _longest_run(periods: Iterable[int]) -> int:
    """Length of the longest run of consecutive integers in ``periods``.

    Trick: after sorting, ``value - position`` is constant inside an unbroken
    run, so grouping by that key splits the numbers into runs.
    """
    ordered = sorted(periods)
    runs = (
        sum(1 for _ in run)
        for _, run in groupby(enumerate(ordered), key=lambda pair: pair[1] - pair[0])
    )
    return max(runs, default=0)


def longest_streak(habit: Habit) -> int:
    """Longest run of consecutive completed periods of one habit (0 if none)."""
    return _longest_run(habit.completed_periods())


def overall_best_streak(habits: Iterable[Habit]) -> Tuple[Optional[Habit], int]:
    """Return ``(habit, length)`` of the longest streak across all habits.

    On a tie the habit that comes first wins. For no habits (or no check-offs)
    the result is ``(None, 0)``.
    """
    scored = map(lambda h: (h, longest_streak(h)), habits)
    return reduce(lambda best, cur: cur if cur[1] > best[1] else best, scored, (None, 0))


def current_streak(habit: Habit, today: date) -> int:
    """Number of consecutive completed periods up to ``today``.

    The period containing ``today`` is still open, so it does not break the
    streak: if it has not been completed yet, counting starts at the previous
    period.
    """
    periods = habit.completed_periods()
    current = habit.periodicity.period_index(today)
    start = current if current in periods else current - 1
    return sum(1 for _ in takewhile(lambda p: p in periods, count(start, -1)))


def _difficulty(habit: Habit, start: date, end: date, today: Optional[date] = None) -> Difficulty:
    """Missed vs. total periods of one habit between ``start`` and ``end`` (inclusive).

    Periods before the habit was created do not count as missed. If ``today``
    is given, its period and all later ones are left out: they are still open
    (or in the future), so they cannot have been missed yet.
    """
    periodicity = habit.periodicity
    first = max(periodicity.period_index(start), periodicity.period_index(habit.created_at))
    last = periodicity.period_index(end)
    if today is not None:
        last = min(last, periodicity.period_index(today) - 1)
    window = range(first, last + 1)
    done = habit.completed_periods()
    return Difficulty(habit, sum(1 for p in window if p not in done), len(window))


def difficulty_ranking(
    habits: Iterable[Habit], start: date, end: date, today: Optional[date] = None
) -> List[Difficulty]:
    """Rank habits by how much the user struggled with them between two dates.

    The habit with the highest share of missed periods comes first (ties are
    broken by the number of missed periods, then by name). Habits that did not
    exist during the window are left out. Pass ``today`` to ignore periods that
    are still open, e.g. when the window is the current month.
    """
    entries = filter(
        lambda d: d.total > 0, map(lambda h: _difficulty(h, start, end, today), habits)
    )
    return sorted(entries, key=lambda d: (-d.miss_rate, -d.missed, d.habit.name))
