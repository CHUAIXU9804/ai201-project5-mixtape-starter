"""
reproduce_feed_bug.py — reproduce Issue #2
("Friends Listening Now shows people from yesterday")

Run from the project root inside your venv:

    python reproduce_feed_bug.py

Calls the ORIGINAL feed_service.get_friends_listening_now() against an isolated
in-memory DB with controlled listen timestamps. Nothing in feed_service.py is
modified.

The bug: RECENT_THRESHOLD = timedelta(hours=24). "Listening now" should be a
short window (minutes), but a 24h cutoff lets a friend who listened many hours
ago (yesterday) still appear as "listening now".
"""

from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User, Song, ListeningEvent, friendships

app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})

with app.app_context():
    db.create_all()
    now = datetime.now(timezone.utc)

    # current user + two friends
    me = User(username="me", email="me@x")
    fresh = User(username="fresh_friend", email="fresh@x")   # listened minutes ago
    stale = User(username="stale_friend", email="stale@x")   # listened ~20h ago (yesterday)
    db.session.add_all([me, fresh, stale])
    db.session.flush()

    # bidirectional friendships (mirrors how seed_data builds them)
    for a, b in [(me, fresh), (me, stale)]:
        db.session.execute(friendships.insert().values(user_id=a.id, friend_id=b.id))
        db.session.execute(friendships.insert().values(user_id=b.id, friend_id=a.id))

    song = Song(title="Test Track", artist="Tester", shared_by=me.id)
    db.session.add(song)
    db.session.flush()

    # fresh friend listened 5 minutes ago -> genuinely "now"
    db.session.add(ListeningEvent(user_id=fresh.id, song_id=song.id,
                                  listened_at=now - timedelta(minutes=5)))
    # stale friend listened 20 hours ago -> yesterday, should NOT be "now"
    db.session.add(ListeningEvent(user_id=stale.id, song_id=song.id,
                                  listened_at=now - timedelta(hours=20)))
    db.session.commit()

    from services.feed_service import get_friends_listening_now
    feed = get_friends_listening_now(me.id)

    print("Friends Listening Now:")
    for entry in feed:
        listened = datetime.fromisoformat(entry["listened_at"])
        if listened.tzinfo is None:          # SQLite returns naive datetimes
            listened = listened.replace(tzinfo=timezone.utc)
        hrs = (now - listened).total_seconds() / 3600
        print(f"    {entry['friend']['username']:14} listened {hrs:.1f} hours ago")

    names = [e["friend"]["username"] for e in feed]
    print()
    if "stale_friend" in names:
        print("BUG REPRODUCED: 'stale_friend' listened 20 hours ago (yesterday) "
              "but still shows up in 'Listening Now'.")
    else:
        print("Stale friend correctly excluded — bug not reproduced.")
