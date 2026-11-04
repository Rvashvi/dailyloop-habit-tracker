"""Custom exceptions used across the habit tracker.

All of them derive from :class:`HabitTrackerError`, so the command line
interface can catch one base class and show a friendly message instead of a
traceback.
"""


class HabitTrackerError(Exception):
    """Base class for all errors raised by the habit tracker."""


class InvalidHabitError(HabitTrackerError, ValueError):
    """A habit was defined with invalid data (e.g. empty name, unknown periodicity)."""


class InvalidCheckOffError(HabitTrackerError, ValueError):
    """A check-off was rejected (in the future, before creation, wrong format)."""


class HabitNotFoundError(HabitTrackerError, LookupError):
    """No habit with the requested id exists."""


class DuplicateHabitError(HabitTrackerError):
    """A habit with the same name already exists."""
