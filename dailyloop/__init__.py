"""DailyLoop: a habit tracking backend with a command line interface.

The package is organised in layers:

* ``cli``          - interface layer (Click commands and interactive menu)
* ``tracker``      - service layer (:class:`HabitTracker`) and ``analytics`` (pure functions)
* ``habit``        - domain layer (:class:`Habit`, :class:`Periodicity`)
* ``repository`` / ``database`` - data layer (SQLite persistence)
* ``demo_habits``  - five predefined habits with four weeks of example data
"""

__version__ = "1.0.0"
