-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY,
    spotify_user_id TEXT NOT NULL UNIQUE,
    display_name TEXT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Artists Table
CREATE TABLE IF NOT EXISTS artists (
    id BIGSERIAL PRIMARY KEY,
    artist_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Albums Table
CREATE TABLE IF NOT EXISTS albums (
    id BIGSERIAL PRIMARY KEY,
    album_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tracks Table
CREATE TABLE IF NOT EXISTS tracks (
    id BIGSERIAL PRIMARY KEY,
    track_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    album_id BIGINT REFERENCES albums(id),
    duration_ms INTEGER,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Track-Artists Table
CREATE TABLE IF NOT EXISTS track_artists (
    track_id BIGINT REFERENCES tracks(id),
    artist_id BIGINT REFERENCES artists(id),
    PRIMARY KEY (track_id, artist_id)
);

-- Contexts Table
CREATE TABLE IF NOT EXISTS contexts (
    id BIGSERIAL PRIMARY KEY,
    context_type TEXT,
    context_uri TEXT UNIQUE,
    name TEXT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Plays Table
CREATE TABLE IF NOT EXISTS plays (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    track_id BIGINT REFERENCES tracks(id),
    played_at TIMESTAMPTZ NOT NULL,
    context_id BIGINT REFERENCES contexts(id),
    raw JSONB NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, track_id, played_at)
);
