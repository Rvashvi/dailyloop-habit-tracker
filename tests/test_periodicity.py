from datetime import date, datetime

import pytest

from dailyloop.exceptions import InvalidHabitError
from dailyloop.habit import Periodicity

DAILY, WEEKLY = Periodicity.DAILY, Periodicity.WEEKLY


def test_daily_same_day_same_index_regardless_of_time():
    assert DAILY.period_index(datetime(2025, 3, 3, 0, 0)) == DAILY.period_index(datetime(2025, 3, 3, 23, 59))


def test_daily_consecutive_days_have_consecutive_indices():
    assert DAILY.period_index(date(2025, 3, 4)) - DAILY.period_index(date(2025, 3, 3)) == 1


def test_daily_index_is_continuous_over_leap_day():
    assert DAILY.period_index(date(2024, 3, 1)) - DAILY.period_index(date(2024, 2, 28)) == 2


def test_weekly_monday_to_sunday_is_one_period():
    monday, sunday = date(2025, 3, 3), date(2025, 3, 9)
    assert WEEKLY.period_index(monday) == WEEKLY.period_index(sunday)


def test_weekly_next_monday_starts_new_period():
    assert WEEKLY.period_index(date(2025, 3, 10)) == WEEKLY.period_index(date(2025, 3, 9)) + 1


def test_weekly_period_spans_year_boundary():
    assert WEEKLY.period_index(date(2024, 12, 30)) == WEEKLY.period_index(date(2025, 1, 5))
    assert WEEKLY.period_index(date(2025, 1, 6)) == WEEKLY.period_index(date(2025, 1, 5)) + 1


@pytest.mark.parametrize("text", ["daily", "DAILY", "  Daily "])
def test_parse_accepts_any_case_and_whitespace(text):
    assert Periodicity.parse(text) is DAILY


def test_parse_passes_enum_through():
    assert Periodicity.parse(WEEKLY) is WEEKLY


def test_parse_rejects_unknown_value():
    with pytest.raises(InvalidHabitError):
        Periodicity.parse("monthly")


def test_unit_names():
    assert (DAILY.unit, WEEKLY.unit) == ("day", "week")
