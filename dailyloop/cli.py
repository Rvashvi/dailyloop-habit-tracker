"""Interface layer: command line interface built with Click.

Run ``habit --help`` (or ``python -m dailyloop --help``) for an overview.
Every command is a thin wrapper: it parses input, calls the
:class:`~dailyloop.tracker.HabitTracker` or the pure functions in
:mod:`dailyloop.analytics`, and formats the result.
"""

import calendar
import functools
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import click

from . import analytics, demo_habits
from .database import DEFAULT_DB_PATH, DatabaseManager
from .exceptions import HabitTrackerError
from .habit import Periodicity
from .repository import HabitRepository
from .tracker import HabitTracker

PERIODICITY = click.Choice([p.value for p in Periodicity], case_sensitive=False)
TIMESTAMP = click.DateTime(formats=["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"])
MONTH = click.DateTime(formats=["%Y-%m"])


@dataclass
class AppContext:
    """Objects shared by all commands during one run."""

    tracker: HabitTracker
    repo: HabitRepository


def _handle_errors(func):
    """Turn application errors into a short message instead of a traceback."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Run the command and convert a HabitTrackerError into a ClickException."""
        try:
            return func(*args, **kwargs)
        except HabitTrackerError as exc:
            raise click.ClickException(str(exc))

    return wrapper


def _plural(count: int, unit: str) -> str:
    """Format ``1 day`` / ``3 days``."""
    return "{} {}{}".format(count, unit, "" if count == 1 else "s")


def _month_bounds(month_start: date):
    """First and last day of the month that contains ``month_start``."""
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start.replace(day=1), month_start.replace(day=last_day)


# ---------------------------------------------------------------------- command group
@click.group()
@click.option(
    "--db", "db_path", envvar="HABIT_DB", default=DEFAULT_DB_PATH, show_default=True,
    type=click.Path(dir_okay=False), help="SQLite database file (or set HABIT_DB).",
)
@click.pass_context
def cli(ctx: click.Context, db_path: str) -> None:
    """DailyLoop: create daily and weekly habits, check them off, analyse your streaks."""
    database = DatabaseManager(db_path)
    ctx.call_on_close(database.close)
    repo = HabitRepository(database)
    ctx.obj = AppContext(tracker=HabitTracker(repo), repo=repo)


@cli.command()
@click.argument("name")
@click.option("--task", required=True, help="What exactly has to be done.")
@click.option("--periodicity", type=PERIODICITY, default="daily", show_default=True,
              help="How often the task has to be completed.")
@click.pass_obj
@_handle_errors
def create(app: AppContext, name: str, task: str, periodicity: str) -> None:
    """Create a new habit called NAME."""
    habit = app.tracker.create_habit(name, task, periodicity)
    click.echo('Created habit #{}: {} ({}).'.format(habit.habit_id, habit.name, habit.periodicity.value))


@cli.command()
@click.argument("habit_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Do not ask for confirmation.")
@click.pass_obj
@_handle_errors
def delete(app: AppContext, habit_id: int, yes: bool) -> None:
    """Delete the habit HABIT_ID together with its history."""
    habit = app.tracker.get_habit(habit_id)
    if not yes:
        click.confirm('Delete "{}" and its history?'.format(habit.name), abort=True)
    app.tracker.delete_habit(habit_id)
    click.echo('Deleted habit #{}: {}.'.format(habit_id, habit.name))


@cli.command()
@click.argument("habit_id", type=int)
@click.option("--at", "at", type=TIMESTAMP, default=None,
              help='Check off at this time instead of now, e.g. "2026-03-05 20:00".')
@click.pass_obj
@_handle_errors
def complete(app: AppContext, habit_id: int, at: Optional[datetime]) -> None:
    """Check off the task of habit HABIT_ID.

    The check-off is recorded now, or at a past time given with --at.
    Follows the activity diagram: the habit is loaded, the timestamp is
    validated, the check-off is stored, and the user is told whether it
    counted a new period or the period was already completed.
    """
    before = app.tracker.get_habit(habit_id)
    timestamp = app.tracker.complete_habit(habit_id, at)
    already_done = before.is_done(timestamp)  # state *before* this check-off
    habit = app.tracker.get_habit(habit_id)
    unit = habit.periodicity.unit
    streak = _plural(analytics.current_streak(habit, date.today()), unit)
    click.echo('Checked off "{}" at {:%Y-%m-%d %H:%M}.'.format(habit.name, timestamp))
    if already_done:
        click.echo("This {} was already completed, so the streak is unchanged: {}.".format(unit, streak))
    else:
        click.echo("New {} counted. Current streak: {}.".format(unit, streak))


@cli.command(name="list")
@click.option("--periodicity", type=PERIODICITY, default=None,
              help="Only show habits with this periodicity.")
@click.pass_obj
@_handle_errors
def list_habits(app: AppContext, periodicity: Optional[str]) -> None:
    """List all habits (optionally only daily or only weekly ones)."""
    habits = analytics.list_habits(app.tracker.get_all())
    if periodicity:
        habits = analytics.select_by_periodicity(habits, Periodicity.parse(periodicity))
    if not habits:
        click.echo("No habits found. Create one with `habit create` or load demo data with `habit populate`.")
        return
    today = date.today()
    width = max(len(h.name) for h in habits)
    click.echo("{:>3}  {:<{w}}  {:<7}  {:<10}  {:<8}  {}".format(
        "ID", "Name", "Period", "Created", "Streak", "Task", w=width))
    for h in habits:
        streak = _plural(analytics.current_streak(h, today), h.periodicity.unit)
        click.echo("{:>3}  {:<{w}}  {:<7}  {:%Y-%m-%d}  {:<8}  {}".format(
            h.habit_id, h.name, h.periodicity.value, h.created_at, streak, h.task, w=width))


@cli.group()
def analyse() -> None:
    """Analyse your habits: streaks and struggles."""


@analyse.command()
@click.option("--habit", "habit_id", type=int, default=None,
              help="Only look at this habit instead of all habits.")
@click.option("--all", "show_all", is_flag=True,
              help="List the longest streak of every habit, not just the best one.")
@click.pass_obj
@_handle_errors
def longest(app: AppContext, habit_id: Optional[int], show_all: bool) -> None:
    """Show the longest streak overall, for one habit (--habit) or for every habit (--all)."""
    if show_all and habit_id is not None:
        raise click.UsageError("Use either --all or --habit, not both.")
    if show_all:
        habits = analytics.list_habits(app.tracker.get_all())
        if not habits:
            click.echo("No habits yet.")
            return
        click.echo("Longest streak of every habit:")
        width = max(len(h.name) for h in habits)
        for h in habits:
            click.echo("{:<{w}}  {}".format(
                h.name, _plural(analytics.longest_streak(h), h.periodicity.unit), w=width))
        return
    if habit_id is not None:
        habit = app.tracker.get_habit(habit_id)
        length = analytics.longest_streak(habit)
        click.echo('Longest streak for "{}": {}.'.format(habit.name, _plural(length, habit.periodicity.unit)))
        return
    habit, length = analytics.overall_best_streak(app.tracker.get_all())
    if habit is None:
        click.echo("No streaks yet: nothing has been checked off.")
    else:
        click.echo('Longest streak overall: "{}" with {}.'.format(habit.name, _plural(length, habit.periodicity.unit)))


@analyse.command()
@click.pass_obj
@_handle_errors
def current(app: AppContext) -> None:
    """Show the current streak of every habit."""
    today = date.today()
    habits = analytics.list_habits(app.tracker.get_all())
    if not habits:
        click.echo("No habits yet.")
    for h in habits:
        click.echo("{:<{w}}  {}".format(
            h.name, _plural(analytics.current_streak(h, today), h.periodicity.unit),
            w=max(len(x.name) for x in habits)))


@analyse.command()
@click.option("--month", type=MONTH, default=None,
              help="Month to analyse as YYYY-MM (default: last month).")
@click.pass_obj
@_handle_errors
def struggles(app: AppContext, month: Optional[datetime]) -> None:
    """Rank habits by how many periods you missed in a month.

    Periods that are still open (today, this week) are not counted as missed.
    """
    if month is None:
        month_start = date.today().replace(day=1) - timedelta(days=1)  # any day of last month
    else:
        month_start = month.date()
    start, end = _month_bounds(month_start)
    ranking = analytics.difficulty_ranking(app.tracker.get_all(), start, end, today=date.today())
    click.echo("Struggle ranking for {:%B %Y} (most missed first):".format(start))
    if not ranking:
        click.echo("  Nothing to rank: no habit has a finished period in that month.")
    for rank, d in enumerate(ranking, start=1):
        click.echo("  {}. {} ({}): missed {} of {} ({:.0%})".format(
            rank, d.habit.name, d.habit.periodicity.value, d.missed,
            _plural(d.total, d.habit.periodicity.unit), d.miss_rate))


@cli.command()
@click.pass_obj
@_handle_errors
def populate(app: AppContext) -> None:
    """Load the five predefined habits with four weeks of example data."""
    before = len(app.tracker.get_all())
    demo_habits.populate(app.repo)
    added = len(app.tracker.get_all()) - before
    if added:
        click.echo("Loaded {} predefined habits with four weeks of example data.".format(added))
    else:
        click.echo("Predefined habits are already loaded.")


# --------------------------------------------------------------------- interactive menu
_MENU = """
==== DailyLoop ====
 1  Create a habit
 2  Check off a habit
 3  Delete a habit
 4  List habits
 5  Longest streak
 6  Current streaks
 7  Struggles last month
 8  Load predefined habits
 0  Quit
"""


def _menu_create(ctx: click.Context) -> None:
    """Ask for name, task and periodicity, then create the habit."""
    name = click.prompt("Name")
    task = click.prompt("Task")
    periodicity = click.prompt("Periodicity", type=PERIODICITY, default="daily")
    ctx.invoke(create, name=name, task=task, periodicity=periodicity)


def _menu_complete(ctx: click.Context) -> None:
    """Ask for a habit id and check it off now."""
    ctx.invoke(complete, habit_id=click.prompt("Habit id", type=int), at=None)


def _menu_delete(ctx: click.Context) -> None:
    """Ask for a habit id and delete it after confirmation."""
    ctx.invoke(delete, habit_id=click.prompt("Habit id", type=int), yes=False)


def _menu_list(ctx: click.Context) -> None:
    """Ask whether to show all, only daily or only weekly habits, then list them."""
    choice = click.prompt("Show which habits", default="all",
                          type=click.Choice(["all"] + [p.value for p in Periodicity], case_sensitive=False))
    ctx.invoke(list_habits, periodicity=None if choice.lower() == "all" else choice)


def _menu_longest(ctx: click.Context) -> None:
    """Show the best streak overall, then the longest streak of every habit."""
    ctx.invoke(longest, habit_id=None, show_all=False)
    if ctx.obj.tracker.get_all():
        ctx.invoke(longest, habit_id=None, show_all=True)


_MENU_ACTIONS = {
    1: _menu_create,
    2: _menu_complete,
    3: _menu_delete,
    4: _menu_list,
    5: _menu_longest,
    6: lambda ctx: ctx.invoke(current),
    7: lambda ctx: ctx.invoke(struggles, month=None),
    8: lambda ctx: ctx.invoke(populate),
}


@cli.command()
@click.pass_context
def menu(ctx: click.Context) -> None:
    """Start a guided, interactive menu (no need to remember commands)."""
    while True:
        click.echo(_MENU)
        choice = click.prompt("Choose an option", type=click.IntRange(0, 8))
        if choice == 0:
            click.echo("Goodbye!")
            return
        try:
            _MENU_ACTIONS[choice](ctx)
        except click.Abort:
            click.echo("Cancelled.")
        except click.ClickException as exc:
            click.echo("Error: {}".format(exc.message), err=True)


def main() -> None:
    """Entry point of the ``habit`` command."""
    cli(prog_name="habit")
