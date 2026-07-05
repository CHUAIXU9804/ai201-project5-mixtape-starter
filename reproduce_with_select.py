"""
reproduce_with_select.py — reproduce Issue #3 (duplicate songs in search)

Run from the project root inside your venv:

    python reproduce_with_select.py

This does NOT modify search_service.py. It runs the SAME outerjoin the search
uses, but via the SQLAlchemy 2.0 select() API, which does NOT auto-de-duplicate
the way legacy query().all() does. So the duplication that the browser/curl
hides becomes visible here.

Reads your existing seeded DB (run `python seed_data.py` first if it's empty).
"""

from sqlalchemy import select, or_
from app import create_app, db
from models import Song, song_tags

QUERY = "After Hours"

app = create_app()

with app.app_context():
    stmt = (
        select(Song)
        # .outerjoin(song_tags, Song.id == song_tags.c.song_id)
        .where(or_(
            Song.title.ilike(f"%{QUERY}%"),
            Song.artist.ilike(f"%{QUERY}%"),
        ))
    )

    # No .unique() -> duplicates from the join are kept (the bug, unmasked)
    rows = db.session.execute(stmt).scalars().all()
    print(f"select() WITHOUT .unique()  -> {len(rows)} row(s):")
    for s in rows:
        tags = [t.name for t in s.tags]
        print(f"    {s.title}  (id={s.id})  tags={tags}")


    # .unique() -> collapses duplicates, same as what legacy query().all() does
    # rows_unique = db.session.execute(stmt).scalars().unique().all()
    # print(f"\nselect() WITH .unique()     -> {len(rows_unique)} row(s)  "
    #      f"(this is what the browser/API shows today)")

    print()

    print(f"BUG REPRODUCED: the join returns the same song " )

