## `streak_service.py`
### AI Usage

I used Claude to understand what each function does within search_service.py, streak_service.py, and feed_service.py. I found the AI's explanation pointed me in the wrong direction when I was trying to reproduce the bug, but the AI did help me to provide suggestions on writing standalone test scripts to reproduce the bugs I selected.

### Issue number and title

**Issue Number:** Issue# 1
**Title:** My listening streak keeps resetting

`streak_service.py` handles listening streak logic for users. Records when an user listens to a song and updates the streak. And the streak increments when a user listens on consecutive calendar days. It resets to 1 if a day is skipped.

**Data Flow:**

`POST /songs/<song_id>/listen` in `routes/songs.py` calls `streak_service.record_listening_event(user_id, song_id)`. The function looks up the user, creates a `ListeningEvent` row for the listen and adds it to the session. Then it delegates streak recalculation to `update_listening_streak`. Stores both the event and the streak change, and returns the event

**Pattern I noticed:**

The time is based on UTC time zone, the streak rules are primarily implemented using if else conditions, and the listening event is stored in db

### How I produced it

**What inputs:**
starting_at_streak = 5, last_listened = 2026-07-03, listened_now : 2026-07-04

starting_at_streak = 5, last_listened = 2026-07-04, listened_now : 2026-07-05

**What sequence of actions:**
Results:
[control] consecutive day, lands on Saturday (expect 5 -> 6):
last listened: Friday 2026-07-03
listened now : Saturday 2026-07-04
streak: 5 -> 6

[BUG] consecutive day, lands on Sunday (expect 5 -> 6, but...):
last listened: Saturday 2026-07-04
listened now : Sunday 2026-07-05
streak: 5 -> 1

**What data condition triggered the behavior:**
Whether the listened_now or last_listened date is a Sunday or not triggered the behavior

### How you found the root cause

I looked at the streak_service.py in services directory, when I see line 73: elif days_since_last == 1 and today.weekday() != 6: I realized this might be a bug since it means that regardless of how many days of streak did the user maintain, when it's Sunday, the streak will get reset. However, it's never mentioned in the function docstring that was the intention

### The root cause

According to the function docstring, when the user listens the song yesterday, the streak days should always increment by 1 regardless of if it's Sunday or (today.weekday() != Sunday) or not, this implementation would cause Sunday unreachable, and always gets resets to 1

## Your fix and side-effect check

I updated line 73 so that it checks whether the user has listened to a song yesterday, and if so, increment the streak days by 1, without checking whether it's a Sunday or not. I also checked record_listening_event and get_streak functions, to make sure these functionalities didn't get impacted

## `feed_service.py`

### Issue number and title

**Issue Number:** Issue# 2
**Title:** Friends Listening Now shows people from yesterday

`service.py` builds the social feed for the user - the "What are my friends listening to" view. It queries `ListeningEvent` rows belonging to the current user's friends and packages the info for the API. Both functions share the same shape: validate the user, get their friend ids, bail out early with `[]` if they have no friends, query listening events, and return a list of `{friend, song, listened_at}` dicts ordered most-recent-first.

**Data Flow:**

When a friend listens to a song, `POST /songs/<song_id>/listen` in `routes/songs.py` calls `streak_service.record_listening_event(friend_id, song_id)` drops a new `ListeningEvent` row into the db. Then `GET /feed/<your_id>/listening-now` in `routes/feed.py` calls `feed_service.get_friends_listening_now(your_id)` looks up the song each friend just listened only if its `listened_at` is within the 24h cutoff. `/feed/<id>/activity` is the same flow minus the cutoff and dedup, capped at `limit=20`.

**Pattern I noticed:**

For the two functions in the file, `get_friends_listening_now(user_id)` is intended for scenarios that if the user has friends and they have listened to songs recently, then return the last song they were listening to. For the `get_activity_feed` function, this is intended for scenarios if the user has friends but the friends haven't listen to any song recently. The logic is similar but the main difference is it returns the most recent N events regardless of when they happened.

### How I produced it:

**What inputs:**
fresh_friend who listened to a song 5 minutes ago, a stale_friend, who listened to a song 20 hours ago

**What sequence of actions:**
Result:
Friends Listening Now:
fresh_friend listened 0.1 hours ago
stale_friend listened 20.0 hours ago

**What data condition triggered the behavior:**
The last_listened data condition triggered the behavior

### How you found the root cause

I looked at the feed_service.py file, and the seed_data.py, I saw in the seed_data.py file that the intention was to return the song that friends have listened within the past 30 minutes, however in the feed_service.py, the threshold window has been set to 24 hours (timedelta(hours=24)), there I suspect this is a bug

### The root cause

According to the function docstring, the intention was to return the song that friends have listened within the past 30 minutes, so when the threshold has been set to 24 hours, it broadens the window, and included songs that friends have listened to yesterday (within 24 hours).

## Your fix and side-effect check

I implemented the change that the RECENT_THRESHOLD in line 13 of feed_service.py has been updated to 30 minutes, that makes the function to work as intended and follows the design. Other related functions such as get_friends_listening_now, get_activity_feed functions are also checked to make sure they do not get impacted.


## `search_service.py`

### Issue number and title

**Issue Number:** Issue# 3
**Title:** The same song keeps showing up twice in search

`search_service.py` handles song lookup logic for the API. Its free-text searching logic goes across the song catalog and fetching a single song by id. It filters to songs by title OR artist.

**Data Flow:**

`GET /songs/search?q=<query>` in `routes/songs.py` calls the `search()` looks up the song to check if the keywords are included in the song's title, then the song is returned in results. Or if the user searches by author's name, it uses the `Song.artist.ilike("%query%")` to search up songs if their author's name matches the keywords given in the user query. Or searches up the song by ID.

**Pattern I noticed:**

For the two functions, `get_song(song_id: str)` returns the single song's information in a dictionary back to the user. While `search_songs(query: str)` returns a list of dictionaries about the songs' information (searched by the author name or the song title) back to the user.

### How I produced it

**What inputs:**
When search for songs with title or author's name contains "Crown”

**What sequence of actions:**
Result:
Crown Heights Anthem (id=04536f42-d3e3-431e-8bed-8c84b13df886) tags=['rap', 'hip-hop', 'boom bap']
Crown Heights Anthem (id=04536f42-d3e3-431e-8bed-8c84b13df886) tags=['rap', 'hip-hop', 'boom bap']
Crown Heights Anthem (id=04536f42-d3e3-431e-8bed-8c84b13df886) tags=['rap', 'hip-hop', 'boom bap']

**What data condition triggered the behavior:**
The keyword query feature that triggers the behavior

### How you found the root cause

I looked at the file search_service.py, and when I read line 27, I realized it could be the bug, because the function docstring mentions that the function searches the songs by author name and title, so involving tags is not necessary needed. It also impacts the original function's intention that one dictionary is generated for each song, since then the dictionaries will get generated depending on the number of tags the songs have

### The root cause

Line 27 in search_service.py joins the tag column into the query, however, the intention of the function is to search songs by author name or song title, tags are never needed, and it produces one row per (song, tag) pair, which is why a 3-tag song generates 3 rows.

## Your fix and side-effect check

I removed line 27 from the search_service.py so it generates one dictionary for each song without using tags, and filters by author name and song title. I also checked the search_songs function, the route /songs/search, and get_song / Songs / <id> route, to make sure these routes don't get impacted with the change.