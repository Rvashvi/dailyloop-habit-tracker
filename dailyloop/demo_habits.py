"""Five predefined habits with four weeks of example tracking data.

The data is deterministic: each habit is described by the day offsets
(0-27) on which it was completed, so the expected streaks are known in
advance. The same data seeds the application (``habit populate``) and serves
as the test fixture for the unit tests.
"""

from datetime import date, datetime, time, timedelta
from typing import NamedTuple, Optional, Tuple

from .habit import Habit, Periodicity
from .repository import HabitRepository

WINDOW_DAYS = 28  # four weeks of example data


class HabitTemplate(NamedTuple):
    """Blueprint of one predefined habit."""

    name: str
    task: str
    periodicity: Periodicity
    at: time                 # time of day of every check-off
    days: Tuple[int, ...]    # day offsets (0-27) on which the task was completed


def _span(*ranges: range) -> Tuple[int, ...]:
    """Combine several ranges into one tuple of day offsets."""
    return tuple(day for r in ranges for day in r)


PREDEFINED_HABITS: Tuple[HabitTemplate, ...] = (
    # Every day except two: runs of 10 and 16 days.
    HabitTemplate("Brush teeth", "Brush teeth for two minutes", Periodicity.DAILY,
                  time(8, 0), _span(range(0, 10), range(12, 28))),
    # Four runs (6, 7, 5, 6 days) separated by single misses.
    HabitTemplate("Read 20 pages", "Read at least 20 pages of a book", Periodicity.DAILY,
                  time(21, 0), _span(range(0, 6), range(7, 14), range(16, 21), range(22, 28))),
    # Hard habit: many short runs (3, 5, 1, 2, 3, 2, 4, 1 days).
    HabitTemplate("Workout 30 minutes", "Complete a 30-minute workout", Periodicity.DAILY,
                  time(18, 30), _span(range(0, 3), range(4, 9), range(10, 11), range(12, 14),
                                      range(15, 18), range(19, 21), range(22, 26), range(27, 28))),
    # Weeks 1, 2 and 4 completed (Saturdays), week 3 missed.
    HabitTemplate("Clean apartment", "Tidy and clean the whole apartment", Periodicity.WEEKLY,
                  time(11, 0), (5, 12, 26)),
    # All four weeks completed (Sundays) plus one extra call in week 2.
    HabitTemplate("Call family", "Phone a family member", Periodicity.WEEKLY,
                  time(19, 0), (6, 9, 13, 20, 27)),
)


def populate(repo: HabitRepository, start: Optional[date] = None) -> None:
    """Store the five predefined habits with their four weeks of check-offs.

    Args:
        repo: Repository to store the habits in. Habits whose name already
            exists are skipped, so calling this twice is harmless.
        start: First day of the four-week window. Defaults to 28 days ago, so
            the data ends yesterday. Use a Monday for week-aligned test data.

    Raises:
        ValueError: if the window would reach into today or the future.
    """
    today = date.today()
    start = start if start is not None else today - timedelta(days=WINDOW_DAYS)
    if start + timedelta(days=WINDOW_DAYS - 1) >= today:
        raise ValueError("The four-week window must end before today.")

    existing = {habit.name for habit in repo.fetch_all()}
    created_at = datetime.combine(start, time.min)
    for template in PREDEFINED_HABITS:
        if template.name in existing:
            continue
        history = [datetime.combine(start + timedelta(days=d), template.at) for d in template.days]
        repo.add(Habit(template.name, template.task, template.periodicity, created_at, history))
