from datetime import datetime, timedelta

import pytest

from dailyloop.exceptions import (DuplicateHabitError, HabitNotFoundError,
                                      InvalidCheckOffError, InvalidHabitError)
from dailyloop.habit import Periodicity


def test_create_habit_stores_it(tracker):
    habit = tracker.create_habit("Read", "Read 20 pages", "daily")
    assert habit.habit_id is not None
    assert tracker.get_habit(habit.habit_id).periodicity is Periodicity.DAILY


def test_create_habit_accepts_enum(tracker):
    assert tracker.create_habit("Run", "Run 5 km", Periodicity.WEEKLY).periodicity is Periodicity.WEEKLY


def test_create_duplicate_rejected(tracker):
    tracker.create_habit("Read", "x", "daily")
    with pytest.raises(DuplicateHabitError):
        tracker.create_habit("Read", "y", "weekly")


def test_create_invalid_rejected_before_storing(tracker):
    with pytest.raises(InvalidHabitError):
        tracker.create_habit("", "x", "daily")
    assert tracker.get_all() == []


def test_complete_habit_persists_checkoff(tracker):
    habit = tracker.create_habit("Read", "x", "daily", created_at=datetime.now() - timedelta(days=3))
    when = datetime.now() - timedelta(days=1)
    assert tracker.complete_habit(habit.habit_id, when) == when
    assert tracker.get_habit(habit.habit_id).history == [when]


def test_complete_habit_defaults_to_now(tracker):
    habit = tracker.create_habit("Read", "x", "daily")
    assert len(tracker.get_habit(habit.habit_id).history) == 0
    tracker.complete_habit(habit.habit_id)
    assert len(tracker.get_habit(habit.habit_id).history) == 1


def test_invalid_checkoff_is_not_stored(tracker):
    habit = tracker.create_habit("Read", "x", "daily")
    with pytest.raises(InvalidCheckOffError):
        tracker.complete_habit(habit.habit_id, datetime.now() + timedelta(days=1))
    assert tracker.get_habit(habit.habit_id).history == []


def test_complete_unknown_habit(tracker):
    with pytest.raises(HabitNotFoundError):
        tracker.complete_habit(42)


def test_delete_habit(tracker):
    habit = tracker.create_habit("Read", "x", "daily")
    tracker.delete_habit(habit.habit_id)
    assert tracker.get_all() == []


def test_delete_unknown_habit(tracker):
    with pytest.raises(HabitNotFoundError):
        tracker.delete_habit(42)
