from datetime import date, datetime, timedelta

import pytest

from dailyloop.demo_habits import PREDEFINED_HABITS, WINDOW_DAYS, populate
from dailyloop.habit import Periodicity

from conftest import DEMO_END, DEMO_START


def test_five_habits_with_at_least_one_daily_and_one_weekly(demo):
    assert len(demo) == 5
    kinds = [h.periodicity for h in demo.values()]
    assert kinds.count(Periodicity.DAILY) == 3 and kinds.count(Periodicity.WEEKLY) == 2


def test_every_habit_has_four_weeks_of_example_data(demo):
    first_day = datetime.combine(DEMO_START, datetime.min.time())
    last_day = datetime.combine(DEMO_END, datetime.max.time())
    for habit in demo.values():
        assert habit.history, habit.name
        assert all(first_day <= ts <= last_day for ts in habit.history), habit.name
        assert habit.created_at == first_day


def test_checkoff_counts(demo):
    counts = {name: len(h.history) for name, h in demo.items()}
    assert counts == {"Brush teeth": 26, "Read 20 pages": 24, "Workout 30 minutes": 21,
                      "Clean apartment": 3, "Call family": 5}


def test_populate_twice_does_not_duplicate(repo, demo):
    populate(repo, start=DEMO_START)
    assert len(repo.fetch_all()) == 5


def test_default_window_ends_yesterday(repo):
    populate(repo)
    latest = max(ts for h in repo.fetch_all() for ts in h.history)
    assert latest.date() == date.today() - timedelta(days=1)


def test_window_reaching_into_today_is_rejected(repo):
    with pytest.raises(ValueError):
        populate(repo, start=date.today() - timedelta(days=WINDOW_DAYS - 2))


def test_templates_use_valid_day_offsets():
    for template in PREDEFINED_HABITS:
        assert all(0 <= d < WINDOW_DAYS for d in template.days)
        assert list(template.days) == sorted(set(template.days))
