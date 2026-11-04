"""Shared fixtures: in-memory database, tracker and the predefined demo habits."""

from datetime import date, timedelta

import pytest

from dailyloop.database import DatabaseManager
from dailyloop.demo_habits import populate
from dailyloop.repository import HabitRepository
from dailyloop.tracker import HabitTracker

DEMO_START = date(2025, 3, 3)                 # a Monday: four full Monday-Sunday weeks
DEMO_END = DEMO_START + timedelta(days=27)    # Sunday, 30 March 2025


@pytest.fixture
def database():
    db = DatabaseManager(":memory:")
    yield db
    db.close()


@pytest.fixture
def repo(database):
    return HabitRepository(database)


@pytest.fixture
def tracker(repo):
    return HabitTracker(repo)


@pytest.fixture
def demo(repo):
    """The five predefined habits (with 4 weeks of data) as a dict keyed by name."""
    populate(repo, start=DEMO_START)
    return {habit.name: habit for habit in repo.fetch_all()}
