"""Analytics tests against the predefined 4-week data (see demo_habits.py).

Expected values are derived by hand from the day offsets of each habit:

    Brush teeth     daily    runs 10, 16            -> longest 16, current 16
    Read 20 pages   daily    runs 6, 7, 5, 6        -> longest 7,  current 6
    Workout 30 minutes daily runs 3,5,1,2,3,2,4,1   -> longest 5,  current 1
    Clean apartment weekly   weeks 1,2,4 done       -> longest 2,  current 1
    Call family     weekly   all four weeks done    -> longest 4,  current 4
"""

from datetime import date, datetime, timedelta

from dailyloop import analytics
from dailyloop.habit import Habit, Periodicity

from conftest import DEMO_END, DEMO_START

EXPECTED_LONGEST = {
    "Brush teeth": 16, "Read 20 pages": 7, "Workout 30 minutes": 5,
    "Clean apartment": 2, "Call family": 4,
}


def test_list_habits_returns_new_list_ordered_by_id(demo):
    shuffled = list(reversed(list(demo.values())))
    result = analytics.list_habits(shuffled)
    assert [h.habit_id for h in result] == sorted(h.habit_id for h in demo.values())
    assert result is not shuffled


def test_select_by_periodicity(demo):
    daily = analytics.select_by_periodicity(demo.values(), Periodicity.DAILY)
    weekly = analytics.select_by_periodicity(demo.values(), Periodicity.WEEKLY)
    assert {h.name for h in daily} == {"Brush teeth", "Read 20 pages", "Workout 30 minutes"}
    assert {h.name for h in weekly} == {"Clean apartment", "Call family"}


def test_longest_streak_per_habit(demo):
    for name, expected in EXPECTED_LONGEST.items():
        assert analytics.longest_streak(demo[name]) == expected, name


def test_overall_best_streak_is_brush_teeth(demo):
    habit, length = analytics.overall_best_streak(demo.values())
    assert (habit.name, length) == ("Brush teeth", 16)


def test_overall_best_streak_without_habits():
    assert analytics.overall_best_streak([]) == (None, 0)


def test_longest_streak_of_habit_without_checkoffs_is_zero():
    assert analytics.longest_streak(Habit("x", "y", "daily", datetime(2025, 1, 1))) == 0


def test_longest_streak_handles_year_boundary():
    habit = Habit("x", "y", "daily", datetime(2024, 12, 1))
    for day in (date(2024, 12, 30), date(2024, 12, 31), date(2025, 1, 1), date(2025, 1, 2)):
        habit.mark_done(datetime.combine(day, datetime.min.time()) + timedelta(hours=9))
    assert analytics.longest_streak(habit) == 4


def test_current_streak_at_end_of_data(demo):
    expected = {"Brush teeth": 16, "Read 20 pages": 6, "Workout 30 minutes": 1,
                "Clean apartment": 1, "Call family": 4}
    for name, value in expected.items():
        assert analytics.current_streak(demo[name], DEMO_END) == value, name


def test_open_period_does_not_break_streak(demo):
    # Monday after the data ends: the new day/week has no check-off yet.
    monday = DEMO_END + timedelta(days=1)
    assert analytics.current_streak(demo["Brush teeth"], monday) == 16
    assert analytics.current_streak(demo["Call family"], monday) == 4


def test_streak_is_broken_once_a_closed_period_is_missed(demo):
    two_days_later = DEMO_END + timedelta(days=2)
    assert analytics.current_streak(demo["Brush teeth"], two_days_later) == 0
    two_weeks_later = DEMO_END + timedelta(days=15)
    assert analytics.current_streak(demo["Call family"], two_weeks_later) == 0


def test_difficulty_ranking_over_whole_window(demo):
    ranking = analytics.difficulty_ranking(demo.values(), DEMO_START, DEMO_END)
    summary = [(d.habit.name, d.missed, d.total) for d in ranking]
    assert summary == [
        ("Workout 30 minutes", 7, 28),
        ("Clean apartment", 1, 4),
        ("Read 20 pages", 4, 28),
        ("Brush teeth", 2, 28),
        ("Call family", 0, 4),
    ]


def test_difficulty_ranking_ignores_periods_before_creation():
    habit = Habit("late", "start", "daily", datetime(2025, 3, 20, 8, 0))
    ranking = analytics.difficulty_ranking([habit], date(2025, 3, 1), date(2025, 3, 31))
    assert (ranking[0].missed, ranking[0].total) == (12, 12)  # 20..31 March


def test_difficulty_ranking_skips_habits_that_did_not_exist_yet():
    habit = Habit("future", "x", "daily", datetime(2025, 5, 1))
    assert analytics.difficulty_ranking([habit], date(2025, 3, 1), date(2025, 3, 31)) == []


def test_analytics_functions_do_not_modify_their_input(demo):
    habits = list(demo.values())
    snapshot = [(h.name, h.history) for h in habits]
    analytics.list_habits(habits)
    analytics.overall_best_streak(habits)
    analytics.difficulty_ranking(habits, DEMO_START, DEMO_END)
    analytics.current_streak(habits[0], DEMO_END)
    assert [(h.name, h.history) for h in habits] == snapshot


def test_difficulty_ranking_with_today_ignores_open_period(demo):
    # Pretend "today" is the last demo day: that day is still open, so only
    # the 27 finished days are judged.
    ranking = analytics.difficulty_ranking(demo.values(), DEMO_START, DEMO_END, today=DEMO_END)
    by_name = {d.habit.name: (d.missed, d.total) for d in ranking}
    assert by_name["Brush teeth"] == (2, 27)
    assert by_name["Workout 30 minutes"] == (7, 27)   # day 27 was done, so 7 misses remain
    assert by_name["Call family"] == (0, 3)            # the fourth week is still open


def test_difficulty_ranking_window_in_the_future_is_empty(demo):
    later = DEMO_END + timedelta(days=30)
    assert analytics.difficulty_ranking(demo.values(), later, later, today=DEMO_END) == []
