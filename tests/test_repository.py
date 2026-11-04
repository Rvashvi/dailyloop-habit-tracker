from datetime import datetime

import pytest

from dailyloop.exceptions import DuplicateHabitError, HabitNotFoundError
from dailyloop.habit import Habit, Periodicity

CREATED = datetime(2025, 3, 3, 7, 0)


def make(name="Read", periodicity="daily", history=None):
    return Habit(name, "Read 20 pages", periodicity, CREATED, history)


def test_add_assigns_id(repo):
    habit = make()
    repo.add(habit)
    assert habit.habit_id is not None


def test_round_trip_preserves_all_fields_and_history(repo):
    stamps = [datetime(2025, 3, 4, 8, 0), datetime(2025, 3, 5, 9, 30)]
    habit = make(periodicity="weekly", history=stamps)
    repo.add(habit)
    loaded = repo.fetch(habit.habit_id)
    assert (loaded.name, loaded.task, loaded.periodicity, loaded.created_at) == (
        "Read", "Read 20 pages", Periodicity.WEEKLY, CREATED)
    assert loaded.history == stamps


def test_fetch_all_returns_habits_ordered_by_id_with_history(repo):
    first, second = make("A", history=[datetime(2025, 3, 4, 8, 0)]), make("B")
    repo.add(first)
    repo.add(second)
    loaded = repo.fetch_all()
    assert [h.name for h in loaded] == ["A", "B"]
    assert len(loaded[0].history) == 1 and loaded[1].history == []


def test_fetch_all_on_empty_database(repo):
    assert repo.fetch_all() == []


def test_duplicate_name_rejected_and_nothing_stored(repo):
    repo.add(make("Read"))
    with pytest.raises(DuplicateHabitError):
        repo.add(make("Read", history=[datetime(2025, 3, 4, 8, 0)]))
    assert len(repo.fetch_all()) == 1


def test_add_completion_persists(repo):
    habit = make()
    repo.add(habit)
    repo.add_completion(habit.habit_id, datetime(2025, 3, 4, 8, 0))
    assert repo.fetch(habit.habit_id).history == [datetime(2025, 3, 4, 8, 0)]


def test_add_completion_for_unknown_habit(repo):
    with pytest.raises(HabitNotFoundError):
        repo.add_completion(999, datetime(2025, 3, 4, 8, 0))


def test_remove_deletes_habit_and_cascades_to_completions(repo, database):
    habit = make(history=[datetime(2025, 3, 4, 8, 0), datetime(2025, 3, 5, 8, 0)])
    repo.add(habit)
    repo.remove(habit.habit_id)
    assert repo.fetch_all() == []
    assert database.connection.execute("SELECT COUNT(*) FROM completion").fetchone()[0] == 0


def test_remove_unknown_habit(repo):
    with pytest.raises(HabitNotFoundError):
        repo.remove(999)


def test_fetch_unknown_habit(repo):
    with pytest.raises(HabitNotFoundError):
        repo.fetch(999)


def test_data_survives_reopening_a_database_file(tmp_path):
    from dailyloop.database import DatabaseManager
    from dailyloop.repository import HabitRepository
    path = tmp_path / "habits.db"
    with DatabaseManager(path) as db:
        HabitRepository(db).add(make("Persistent", history=[datetime(2025, 3, 4, 8, 0)]))
    with DatabaseManager(path) as db:
        loaded = HabitRepository(db).fetch_all()
    assert [h.name for h in loaded] == ["Persistent"] and len(loaded[0].history) == 1
