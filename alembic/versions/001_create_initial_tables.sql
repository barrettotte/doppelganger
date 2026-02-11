-- initial schema

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(20) NOT NULL UNIQUE,
    username VARCHAR(100),
    blacklisted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_discord_id ON users (discord_id);

CREATE TABLE characters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    reference_audio_path VARCHAR(500) NOT NULL,
    engine VARCHAR(20) NOT NULL DEFAULT 'chatterbox',
    tts_exaggeration REAL,
    tts_cfg_weight REAL,
    tts_temperature REAL,
    tts_repetition_penalty REAL,
    tts_top_p REAL,
    tts_frequency_penalty REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tts_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    character VARCHAR(100) NOT NULL,
    text VARCHAR(3000) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER
);
CREATE INDEX idx_tts_requests_user_id ON tts_requests (user_id);
CREATE INDEX idx_tts_requests_status ON tts_requests (status);

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log (created_at);
