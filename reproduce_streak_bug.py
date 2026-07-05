"""
reproduce_streak_bug.py — reproduce Issue #1 (listening streak keeps resetting)

Run from the project root inside your venv:

    python reproduce_streak_bug.py

Calls the ORIGINAL streak_service.update_listening_streak() with a controlled
`now`, so the bug is deterministic and does NOT depend on today's real date.
Nothing in streak_service.py is modified.

The bug: update_listening_streak() only increments the streak when
`today.weekday() != 6`. weekday() == 6 is SUNDAY, so a normal consecutive-day
listen that lands on a Sunday resets the streak to 1 instead of incrementing.
"""

from datetime import datetime, timezone
from app import create_app, db
from models import User
from services.streak_service import update_listening_streak

app = create_app()

with app.app_context():
    def run(label, last_listened, now, starting_streak=5):
        user = User(username="t", email="t@t", listening_streak=starting_streak)
        user.last_listened_at = last_listened
        update_listening_streak(user, now)
        print(f"{label}\n"
              f"    last listened: {last_listened:%A %Y-%m-%d}\n"
              f"    listened now : {now:%A %Y-%m-%d}\n"
              f"    streak: {starting_streak} -> {user.listening_streak}\n")

    # CONTROL: Friday -> Saturday (consecutive day, not Sunday) => should increment
    run("[control] consecutive day, lands on Saturday (expect 5 -> 6):",
        datetime(2026, 7, 3, 12, tzinfo=timezone.utc),   # Friday
        datetime(2026, 7, 4, 12, tzinfo=timezone.utc))   # Saturday

    # BUG: Saturday -> Sunday (consecutive day, lands on Sunday) => wrongly resets
    run("[BUG] consecutive day, lands on Sunday (expect 5 -> 6, but...):",
        datetime(2026, 7, 4, 12, tzinfo=timezone.utc),   # Saturday
        datetime(2026, 7, 5, 12, tzinfo=timezone.utc))   # Sunday (weekday()==6)

    print("If the Sunday case shows streak reset to 1 while the control "
          "incremented, Issue #1 is reproduced.")
