from datetime import date, datetime, timedelta, timezone

import pytest

from dailyloop.exceptions import InvalidCheckOffError, InvalidHabitError
from dailyloop.habit import Habit, Periodicity

CREATED = datetime(2025, 3, 3, 7, 0)


def make(periodicity=Periodicity.DAILY):
    return Habit("Read", "Read 20 pages", periodicity, CREATED)


def test_new_habit_has_no_id_and_empty_history():
    habit = make()
    assert habit.habit_id is None and habit.history == []


def test_name_and_task_are_trimmed():
    habit = Habit("  Read  ", " Read 20 pages ", "daily", CREATED)
    assert (habit.name, habit.task) == ("Read", "Read 20 pages")


@pytest.mark.parametrize("name,task", [("", "x"), ("   ", "x"), ("x", ""), ("x", "   ")])
def test_empty_name_or_task_rejected(name, task):
    with pytest.raises(InvalidHabitError):
        Habit(name, task, "daily", CREATED)


def test_unknown_periodicity_rejected():
    with pytest.raises(InvalidHabitError):
        Habit("x", "y", "yearly", CREATED)


def test_created_at_defaults_to_now():
    before = datetime.now()
    habit = Habit("x", "y", "daily")
    assert before <= habit.created_at <= datetime.now()


def test_mark_done_returns_and_records_timestamp():
    habit = make()
    stamp = datetime(2025, 3, 4, 20, 0)
    assert habit.mark_done(stamp) == stamp
    assert habit.history == [stamp]


def test_mark_done_defaults_to_now():
    habit = Habit("x", "y", "daily")
    before = datetime.now()
    stamp = habit.mark_done()
    assert before <= stamp <= datetime.now()


def test_history_stays_sorted_when_backdating():
    habit = make()
    late, early = datetime(2025, 3, 6, 9, 0), datetime(2025, 3, 4, 9, 0)
    habit.mark_done(late)
    habit.mark_done(early)
    assert habit.history == [early, late]


def test_several_checkoffs_in_one_period_count_once():
    habit = make()
    habit.mark_done(datetime(2025, 3, 4, 8, 0))
    habit.mark_done(datetime(2025, 3, 4, 20, 0))
    assert len(habit.history) == 2
    assert len(habit.completed_periods()) == 1


def test_weekly_habit_counts_two_days_of_one_week_once():
    habit = make(Periodicity.WEEKLY)
    habit.mark_done(datetime(2025, 3, 4, 8, 0))
    habit.mark_done(datetime(2025, 3, 8, 8, 0))
    assert len(habit.completed_periods()) == 1


def test_checkoff_before_creation_rejected():
    with pytest.raises(InvalidCheckOffError):
        make().mark_done(CREATED - timedelta(minutes=1))


def test_checkoff_in_future_rejected():
    with pytest.raises(InvalidCheckOffError):
        make().mark_done(datetime.now() + timedelta(days=1))


def test_timezone_aware_timestamp_rejected():
    with pytest.raises(InvalidCheckOffError):
        make().mark_done(datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc))


def test_rejected_checkoff_leaves_history_unchanged():
    habit = make()
    with pytest.raises(InvalidCheckOffError):
        habit.mark_done(CREATED - timedelta(days=1))
    assert habit.history == []


def test_is_done_daily():
    habit = make()
    habit.mark_done(datetime(2025, 3, 4, 8, 0))
    assert habit.is_done(date(2025, 3, 4)) is True
    assert habit.is_done(date(2025, 3, 5)) is False


def test_is_done_weekly_covers_whole_week():
    habit = make(Periodicity.WEEKLY)
    habit.mark_done(datetime(2025, 3, 5, 8, 0))
    assert habit.is_done(date(2025, 3, 3)) and habit.is_done(date(2025, 3, 9))
    assert not habit.is_done(date(2025, 3, 10))


def test_history_property_returns_a_copy():
    habit = make()
    habit.mark_done(datetime(2025, 3, 4, 8, 0))
    habit.history.clear()
    assert len(habit.history) == 1
