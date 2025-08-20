-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spotify_user_id TEXT NOT NULL UNIQUE,
    display_name TEXT,
    inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Listening history table
CREATE TABLE IF NOT EXISTS plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),

    -- Track
    track_id TEXT NOT NULL,
    track_name TEXT NOT NULL,

    -- Artist
    artist_id TEXT NOT NULL,     
    artist_name TEXT NOT NULL,

    -- Album
    album_id TEXT,
    album_name TEXT,

    -- Metadata
    played_at DATETIME NOT NULL,
    duration_ms INTEGER,
    context_uri TEXT,
    inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, track_id, played_at)
);

