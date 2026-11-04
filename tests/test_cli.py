"""End-to-end tests of the command line interface using Click's CliRunner."""

import pytest
from click.testing import CliRunner

from dailyloop.cli import cli


@pytest.fixture
def run(tmp_path):
    runner = CliRunner()
    db = str(tmp_path / "test.db")

    def _run(*args, **kwargs):
        return runner.invoke(cli, ["--db", db, *args], **kwargs)

    return _run


def test_create_complete_and_list(run):
    assert 'Created habit #1: Read (daily).' in run("create", "Read", "--task", "Read 20 pages").output
    result = run("complete", "1")
    assert result.exit_code == 0 and "Current streak: 1 day." in result.output
    listing = run("list").output
    assert "Read" in listing and "daily" in listing


def test_create_weekly_and_filter_list(run):
    run("create", "Read", "--task", "x")
    run("create", "Clean", "--task", "y", "--periodicity", "weekly")
    weekly = run("list", "--periodicity", "weekly").output
    assert "Clean" in weekly and "Read" not in weekly


def test_list_without_habits_shows_hint(run):
    assert "habit populate" in run("list").output


def test_duplicate_name_shows_friendly_error(run):
    run("create", "Read", "--task", "x")
    result = run("create", "Read", "--task", "y")
    assert result.exit_code == 1
    assert "already exists" in result.output and "Traceback" not in result.output


def test_complete_unknown_habit(run):
    result = run("complete", "99")
    assert result.exit_code == 1 and "No habit with id 99" in result.output


def test_complete_in_future_rejected(run):
    run("create", "Read", "--task", "x")
    result = run("complete", "1", "--at", "2999-01-01 10:00")
    assert result.exit_code == 1 and "future" in result.output


def test_delete_asks_for_confirmation(run):
    run("create", "Read", "--task", "x")
    assert run("delete", "1", input="n\n").exit_code != 0
    assert "Read" in run("list").output
    assert run("delete", "1", input="y\n").exit_code == 0
    assert "No habits found" in run("list").output


def test_delete_with_yes_flag(run):
    run("create", "Read", "--task", "x")
    assert "Deleted habit #1" in run("delete", "1", "--yes").output


def test_populate_then_analyse(run):
    assert "Loaded 5 predefined habits" in run("populate").output
    assert "already loaded" in run("populate").output
    assert 'Longest streak overall: "Brush teeth" with 16 days.' in run("analyse", "longest").output
    assert 'Longest streak for "Read 20 pages": 7 days.' in run("analyse", "longest", "--habit", "2").output
    current = run("analyse", "current").output
    assert "Brush teeth" in current and "Call family" in current
    ranking = run("analyse", "struggles", "--month", "2020-01")
    assert ranking.exit_code == 0 and "Nothing to rank" in ranking.output


def test_longest_without_data(run):
    assert "nothing has been checked off" in run("analyse", "longest").output


def test_longest_all_lists_every_habit(run):
    run("populate")
    result = run("analyse", "longest", "--all")
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert lines[0] == "Longest streak of every habit:"
    assert lines[1:] == [
        "Brush teeth         16 days",
        "Read 20 pages       7 days",
        "Workout 30 minutes  5 days",
        "Clean apartment     2 weeks",
        "Call family         4 weeks",
    ]


def test_longest_all_without_habits(run):
    assert "No habits yet." in run("analyse", "longest", "--all").output


def test_longest_all_and_habit_cannot_be_combined(run):
    result = run("analyse", "longest", "--all", "--habit", "1")
    assert result.exit_code == 2 and "either --all or --habit" in result.output


def test_invalid_periodicity_rejected_by_click(run):
    assert run("create", "Read", "--task", "x", "--periodicity", "monthly").exit_code == 2


def test_menu_can_create_list_and_quit(run):
    result = run("menu", input="1\nRead\nRead 20 pages\ndaily\n4\n\n0\n")
    assert result.exit_code == 0
    assert "Created habit #1" in result.output and "Goodbye!" in result.output


def test_menu_longest_shows_overall_and_every_habit(run):
    run("populate")
    result = run("menu", input="5\n0\n")
    assert 'Longest streak overall: "Brush teeth" with 16 days.' in result.output
    assert "Longest streak of every habit:" in result.output
    assert "Workout 30 minutes  5 days" in result.output


def test_menu_longest_without_habits(run):
    result = run("menu", input="5\n0\n")
    assert "No streaks yet" in result.output
    assert "Longest streak of every habit" not in result.output


def test_menu_list_can_filter_by_periodicity(run):
    run("populate")
    result = run("menu", input="4\nweekly\n0\n")
    assert "Clean apartment" in result.output and "Call family" in result.output
    assert "Brush teeth" not in result.output


def test_menu_shows_errors_and_keeps_running(run):
    result = run("menu", input="2\n99\n0\n")
    assert "No habit with id 99" in result.output and "Goodbye!" in result.output


def test_second_checkoff_same_day_leaves_streak_unchanged(run):
    run("create", "Read", "--task", "x")
    assert "New day counted. Current streak: 1 day." in run("complete", "1").output
    second = run("complete", "1").output
    assert "already completed, so the streak is unchanged: 1 day." in second


def test_list_shows_current_streak_column(run):
    run("create", "Read", "--task", "x")
    run("complete", "1")
    lines = run("list").output.splitlines()
    assert "Streak" in lines[0] and "1 day" in lines[1]


def test_struggles_for_current_month_ignores_open_and_future_days(run):
    from datetime import date
    run("create", "Read", "--task", "x")  # created today, nothing checked off
    this_month = date.today().strftime("%Y-%m")
    result = run("analyse", "struggles", "--month", this_month)
    # today is still open and the rest of the month lies in the future, so there
    # is nothing the user could have missed yet
    assert "Nothing to rank" in result.output
