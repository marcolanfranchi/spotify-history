-- V2: normalized artist / album / track tables, genres, play context type.
-- Additive only: existing `plays` columns are untouched so the email, export and
-- older tooling keep working.

-- Artists. `enriched_at` is NULL until GET /artists/{id} has been applied.
CREATE TABLE IF NOT EXISTS artists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    image_url TEXT,
    -- best-effort: Spotify has deprecated these and may stop returning them
    popularity INTEGER,
    followers_total INTEGER,
    enriched_at DATETIME,
    inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artist_genres (
    artist_id TEXT NOT NULL REFERENCES artists(id),
    genre TEXT NOT NULL,
    PRIMARY KEY (artist_id, genre)
);

-- Albums. `enriched_at` is NULL until album details are known (set immediately
-- for albums seen via recently-played, which carries the same fields).
CREATE TABLE IF NOT EXISTS albums (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    album_type TEXT,
    release_date TEXT,
    release_date_precision TEXT,
    total_tracks INTEGER,
    image_url TEXT,
    enriched_at DATETIME,
    inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    album_id TEXT REFERENCES albums(id),
    duration_ms INTEGER,
    explicit INTEGER,
    track_number INTEGER,
    disc_number INTEGER,
    isrc TEXT,
    inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- A track can have several artists; position 0 is the main (first-listed) artist.
CREATE TABLE IF NOT EXISTS track_artists (
    track_id TEXT NOT NULL REFERENCES tracks(id),
    artist_id TEXT NOT NULL REFERENCES artists(id),
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (track_id, artist_id)
);

ALTER TABLE plays ADD COLUMN context_type TEXT;

CREATE INDEX IF NOT EXISTS idx_plays_played_at ON plays(played_at);
CREATE INDEX IF NOT EXISTS idx_plays_artist_id ON plays(artist_id);
CREATE INDEX IF NOT EXISTS idx_plays_album_id ON plays(album_id);
CREATE INDEX IF NOT EXISTS idx_artist_genres_genre ON artist_genres(genre);

-- Seed from existing plays (no API calls). Using the most recent row per id for
-- names; SQLite returns bare columns from the row holding MAX(played_at).
INSERT OR IGNORE INTO artists (id, name)
SELECT artist_id, artist_name FROM (
    SELECT artist_id, artist_name, MAX(played_at) FROM plays GROUP BY artist_id
);

INSERT OR IGNORE INTO albums (id, name)
SELECT album_id, album_name FROM (
    SELECT album_id, album_name, MAX(played_at) FROM plays
    WHERE album_id IS NOT NULL GROUP BY album_id
);

INSERT OR IGNORE INTO tracks (id, name, album_id, duration_ms)
SELECT track_id, track_name, album_id, duration_ms FROM (
    SELECT track_id, track_name, album_id, duration_ms, MAX(played_at)
    FROM plays GROUP BY track_id
);

-- Historical plays only recorded the first artist; position 0 is correct for those.
INSERT OR IGNORE INTO track_artists (track_id, artist_id, position)
SELECT DISTINCT track_id, artist_id, 0 FROM plays;
