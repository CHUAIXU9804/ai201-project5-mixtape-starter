**streak_service.py**
streak_service.py handles listening streak logic for users. Records when an user listens to a song and updates the streak. And the streak increments when a user listens on consecutive calendar days. It resets to 1 if a day is skipped.

Data Flow:
POST /songs/<song_id>/listen in routes/songs.py calls streak_service.record_listening_event(user_id, song_id). The function looks up the user, creates a ListeningEvent row for the listen and adds it to the session. Then it delegates streak recalculation to update_listening_streak. Stores both the event and the streak change, and returns the event

Pattern I noticed: The time is based on UTC time zone, the streak rules are primarily implemented using if else conditions, and the listening event is stored in db

**feed_service.py**
service.py builds the social feed for the user - the "What are my friends listening to" view. It queries ListeningEvent rows belonging to the current user's friends and packages the info for the API. Both functions share the same shape: validate the user, get their friend ids, bail out early with [] if they have no friends, query listening events, and return a list of {friend, song, listened_at} dicts ordered most-recent-first.

Data Flow:
When a friend listens to a song, POST /songs/<song_id>/listen in routes/songs.py calls streak_service.record_listening_event(friend_id, song_id) drops a new ListeningEvent row into the db. Then GET /feed/<your_id>/listening-now in routes/feed.py calls feed_service.get_friends_listening_now(your_id) looks up the song each friend just listened only if its listened_at is within the 24h cutoff. /feed/<id>/activity is the same flow minus the cutoff and dedup, capped at limit=20.

Pattern I noticed: For the two functions in the file, get_friends_listening_now(user_id) is intended for scenarios that if the user has friends and they have listened to songs recently, then return the last song they were listening to. For the get_activity_feed function, this is intended for scenarios if the user has friends but the friends haven't listen to any song recently. The logic is similar but the main difference is it returns the most recent N events regardless of when they happened.


**search_service.py**
search_service.py handles song lookup logic for the API. Its free-text searching logic goes across the song catalog and fetching a single song by id. It filters to songs by title OR artist.

Data Flow:
GET /songs/search?q=<query> in routes/songs.py calls the search() looks up the song to check if the keywords are included in the song's title, then the song is returned in results. Or if the user searches by author's name, it uses the Song.artist.ilike("%query%") to search up songs if their author's name matches the keywords given in the user query. Or searches up the song by ID.

Pattern I noticed:
For the two functions, get_song(song_id: str) returns the single song's information in a dictionary back to the user. While search_songs(query: str) returns a list of dictionaries about the songs' information (searched by the author name or the song title) back to the user.




