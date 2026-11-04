# DailyLoop: a habit tracking app

DailyLoop is a habit tracking backend with a command line interface, written in Python.

Users define **daily** or **weekly** habits, check them off, and analyse their behaviour:
longest streaks, current streaks, and the habits they struggled with most last month.
Data is stored in a local SQLite database, so all habits are still there the next time the
program starts.

## Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Running DailyLoop](#running-dailyloop)
5. [Commands](#commands)
6. [The interactive menu](#the-interactive-menu)
7. [Example session](#example-session)
8. [How to create a habit and complete a task](#how-to-create-a-habit-and-complete-a-task)
9. [Predefined habits](#predefined-habits)
10. [Streak rules](#streak-rules)
11. [Running the tests](#running-the-tests)
12. [Project structure and design](#project-structure-and-design)
13. [Troubleshooting](#troubleshooting)
14. [Limitations](#limitations)

## Features

- Create and delete habits with a task description and a periodicity (daily or weekly)
- Check off a task at any time (now, or at a past time with `--at`)
- See every habit with its creation date and current streak (`habit list`), or only the
  daily or only the weekly ones
- Five predefined habits with four weeks of example data (`habit populate`)
- Analytics written in the functional paradigm: list all habits, filter by periodicity,
  longest streak (overall, of one habit, or of every habit), current streaks, and a ranking
  of the habits that were missed most in a month
- Interactive menu for users who do not want to remember commands
- Friendly error messages instead of tracebacks
- Unit test suite (pytest, 98 tests), including end-to-end tests of the CLI

## Requirements

- Python 3.7 or later. The test suite passes on Python 3.8, 3.11, 3.12, 3.13 and 3.14
  (clean install in a fresh virtual environment).
- [Click](https://click.palletsprojects.com/) 8 (installed automatically, see below)
- pytest (only needed to run the tests, installed with the `dev` extra)

## Installation

### 1. Get the code

Either clone the repository with Git, using the address shown under the green **Code**
button on the repository page:

```bash
git clone <repository address>
cd dailyloop-habit-tracker
```

or download it from GitHub (**Code -> Download ZIP**), unzip it and open a terminal in the
unzipped folder (the one that contains `pyproject.toml`).

### 2. Create and activate a virtual environment (recommended)

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (Command Prompt):

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell refuses to run the activation script, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.
The prompt now starts with `(.venv)`.

### 3. Install DailyLoop

```bash
python -m pip install --upgrade pip      # editable installs need pip 21.3 or later
pip install -e ".[dev]"                  # DailyLoop, Click and pytest
```

This installs the `habit` command. To use DailyLoop without installing the package, run
`pip install -r requirements-dev.txt` instead and start the app with `python -m dailyloop`
(from the project folder) wherever this README says `habit`.

## Running DailyLoop

```bash
habit --help                    # overview of all commands
habit populate                  # load the five predefined habits (optional)
habit menu                      # guided, interactive menu
```

The database file `habits.db` is created in the current folder on first use. Always start
DailyLoop from the same folder to see the same habits, or choose a fixed file with
`habit --db path/to/file.db ...` or the environment variable `HABIT_DB`.

## Commands

| Command | What it does |
|---|---|
| `habit create NAME --task TEXT [--periodicity daily\|weekly]` | Create a habit (default: daily) |
| `habit complete ID [--at "YYYY-MM-DD HH:MM"]` | Check off a task now, or at a past time |
| `habit delete ID [--yes]` | Delete a habit and its history (asks for confirmation) |
| `habit list [--periodicity daily\|weekly]` | List all habits with their current streak, or only daily / weekly ones |
| `habit analyse longest` | Longest streak across all habits |
| `habit analyse longest --habit ID` | Longest streak of one habit |
| `habit analyse longest --all` | Longest streak of every habit |
| `habit analyse current` | Current streak of every habit |
| `habit analyse struggles [--month YYYY-MM]` | Habits missed most (default: last month) |
| `habit populate` | Load the five predefined habits with four weeks of data |
| `habit menu` | Interactive menu |

Every command has its own help, for example `habit complete --help`. Habit ids are shown by
`habit list`.

## The interactive menu

`habit menu` shows a numbered menu and asks for everything it needs:

```
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
```

- **1** asks for a name, a task and the periodicity (press Enter for `daily`).
- **2** and **3** ask for a habit id; deleting asks for confirmation first.
- **4** asks whether to show `all`, `daily` or `weekly` habits (press Enter for `all`).
- **5** shows the best streak overall and the longest streak of every habit.
- **8** loads the predefined habits; doing it twice is harmless.

Mistakes (an unknown id, a future date) are reported, and the menu keeps running.

## Example session

```
$ habit populate
Loaded 5 predefined habits with four weeks of example data.
$ habit list
 ID  Name                Period   Created     Streak    Task
  1  Brush teeth         daily    2026-09-21  16 days   Brush teeth for two minutes
  2  Read 20 pages       daily    2026-09-21  6 days    Read at least 20 pages of a book
  3  Workout 30 minutes  daily    2026-09-21  1 day     Complete a 30-minute workout
  4  Clean apartment     weekly   2026-09-21  1 week    Tidy and clean the whole apartment
  5  Call family         weekly   2026-09-21  4 weeks   Phone a family member
$ habit create Stretch --task "Stretch for 10 minutes" --periodicity daily
Created habit #6: Stretch (daily).
$ habit complete 6
Checked off "Stretch" at 2026-10-19 18:18.
New day counted. Current streak: 1 day.
$ habit complete 6
Checked off "Stretch" at 2026-10-19 18:18.
This day was already completed, so the streak is unchanged: 1 day.
$ habit analyse longest
Longest streak overall: "Brush teeth" with 16 days.
$ habit analyse longest --habit 2
Longest streak for "Read 20 pages": 7 days.
$ habit analyse longest --all
Longest streak of every habit:
Brush teeth         16 days
Read 20 pages       7 days
Workout 30 minutes  5 days
Clean apartment     2 weeks
Call family         4 weeks
Stretch             1 day
$ habit analyse struggles --month 2026-10
Struggle ranking for October 2026 (most missed first):
  1. Clean apartment (weekly): missed 1 of 3 weeks (33%)
  2. Workout 30 minutes (daily): missed 5 of 18 days (28%)
  3. Read 20 pages (daily): missed 3 of 18 days (17%)
  4. Brush teeth (daily): missed 2 of 18 days (11%)
  5. Call family (weekly): missed 0 of 3 weeks (0%)
```

Dates and struggle numbers in a new run will differ: the example data always covers
the four weeks before yesterday, and periods that are still open are not counted as missed.
The streak lengths of the predefined habits are always the same.

## How to create a habit and complete a task

1. `habit create "Read" --task "Read 20 pages" --periodicity daily` creates the habit and
   prints its id (use `--periodicity weekly` for a weekly habit).
2. `habit complete 1` checks it off now. Use `--at "2026-03-05 20:00"` to record a
   check-off in the past. Check-offs in the future, or before the habit was created, are
   rejected with an error message.
3. A task has to be checked off **at least once per period**: once per calendar day for a
   daily habit, once per Monday-to-Sunday week for a weekly habit. A second check-off in the
   same period is stored, but the streak does not change. DailyLoop reports which case
   applied.
4. `habit delete 1` removes the habit and all its check-offs (after confirmation).

## Predefined habits

`habit populate` stores these five habits with four weeks of tracking data. The same data
is the **test fixture** of the unit tests (`tests/conftest.py`).

| Habit | Periodicity | Pattern in the 4 weeks | Longest streak |
|---|---|---|---|
| Brush teeth | daily | all days except two | 16 days |
| Read 20 pages | daily | four runs separated by single misses | 7 days |
| Workout 30 minutes | daily | many short runs (a "hard" habit) | 5 days |
| Clean apartment | weekly | weeks 1, 2 and 4 completed, week 3 missed | 2 weeks |
| Call family | weekly | all four weeks (one extra call in week 2) | 4 weeks |

## Streak rules

- A **period** is one calendar day (daily habits) or one Monday-to-Sunday week (weekly habits).
- A period is **completed** if the task was checked off at least once in it. More check-offs
  in the same period are stored, but count once.
- A habit is **broken** when a finished period has no check-off.
- A **streak** is a run of consecutive completed periods.
- The **current, still open period does not break a streak**. If the teeth have not been
  brushed yet today, yesterday's streak is still alive. For the same reason, the struggle
  ranking does not count open periods as missed.

## Running the tests

From the project folder, with the virtual environment activated:

```bash
pytest
```

The suite (98 tests) covers period calculation, check-off validation, all analytics
functions against the predefined data, the SQLite repository (including cascade delete),
the service layer, and the CLI and menu (via Click's `CliRunner`). Every test uses a fresh
in-memory or temporary database, so the personal `habits.db` is never touched. Measured line
coverage of the package is 97 % (`pip install pytest-cov`, then `pytest --cov=dailyloop`).

## Project structure and design

```
pyproject.toml       Package metadata, dependencies and the `habit` command
requirements.txt     Runtime dependency (Click)
requirements-dev.txt Runtime and test dependencies
dailyloop/
    cli.py           Interface layer: Click commands and interactive menu
    tracker.py       Service layer: HabitTracker (create, delete, complete, get)
    analytics.py     Functional analytics module (pure functions)
    habit.py         Domain layer: Habit class and Periodicity enum
    repository.py    Data layer: HabitRepository (all SQL)
    database.py      DatabaseManager: SQLite connection and schema
    demo_habits.py   Five predefined habits with four weeks of data
    exceptions.py    Custom exceptions
tests/               pytest test suite (one file per module)
```

### Design overview

```
cli  -->  HabitTracker  -->  HabitRepository  -->  DatabaseManager (SQLite)
 |             |                    |
 |             +-->  Habit  <-------+          (Habit uses Periodicity)
 +-->  analytics (reads Habit objects, never modifies them)
```

- **Object-oriented core:** `Habit` and `Periodicity` hold the domain rules and have no
  database or user-interface code. `HabitTracker` coordinates use cases.
- **Functional analytics:** all functions in `analytics.py` are pure and use `map`, `filter`,
  `sorted`, `functools.reduce` and `itertools`. The four required functions are
  `list_habits`, `select_by_periodicity`, `overall_best_streak` and `longest_streak`;
  `current_streak` and `difficulty_ranking` add the current streaks and the struggle ranking.
- **Period index:** every timestamp is converted to an integer period index, so consecutive
  periods are consecutive integers and streaks work across month and year boundaries.
- **Streaks are derived, never stored,** so they cannot get out of sync with the check-offs.
- **SQLite** gives integrity (unique names, cascade delete) without extra installation.
- **Custom exceptions** (`exceptions.py`) are raised in the domain and data layers and turned
  into short messages by the CLI.

### Database schema

```
habit(id, name UNIQUE, task, periodicity, created_at)
completion(id, habit_id -> habit.id ON DELETE CASCADE, completed_at)
```

Timestamps are stored as ISO 8601 text in local time.

## Troubleshooting

| Problem | Solution |
|---|---|
| `habit` is not recognized / command not found | Activate the virtual environment (step 2) or use `python -m dailyloop` instead of `habit`. |
| `Error: No habit with id N.` | The id does not exist in this database. Run `habit list` to see the ids, or `habit populate` to load the example habits. |
| Habits seem to be gone | `habits.db` is created in the folder DailyLoop is started from. Start it from the same folder, or use `--db` / `HABIT_DB`. |
| Starting again with an empty database | Delete `habits.db` (it is recreated empty on the next start). |
| `pip install -e` fails | Upgrade pip first: `python -m pip install --upgrade pip`. |
| A note "Editable installation ... folders with the same name" appears during installation | This is an information message from setuptools and can be ignored. |

## Limitations

- Local time only; timezone-aware timestamps are rejected.
- Habits cannot be renamed or edited after creation (delete and recreate).
- Only daily and weekly periodicities exist. Adding more means extending `Periodicity.period_index`.
