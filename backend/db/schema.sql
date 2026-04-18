-- Realm of Ashes – Database Schema
-- SQLite, created on first run via database.py:init_db()

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Players table: tracks each browser session as a player
CREATE TABLE IF NOT EXISTS players (
    id          TEXT PRIMARY KEY,                      -- UUID generated client-side on first visit
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP,
    ash_level   INTEGER DEFAULT 0,                     -- 0-10, modified by in-game choices
    ash_log     TEXT    DEFAULT '[]'                   -- JSON array of ash change events for context
);

-- NPC memory table: what each NPC remembers about each player
CREATE TABLE IF NOT EXISTS npc_memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id   TEXT NOT NULL,
    npc_id      TEXT NOT NULL,                         -- matches npc_id in npcs.json
    memory_text TEXT NOT NULL,                         -- single fact, max 120 chars
    memory_type TEXT DEFAULT 'general',                -- 'general' | 'emotional' | 'ash_event'
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Dialogue log: full conversation history per player per NPC
CREATE TABLE IF NOT EXISTS dialogue_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id         TEXT NOT NULL,
    npc_id            TEXT NOT NULL,
    role              TEXT NOT NULL,                   -- 'player' | 'npc'
    content           TEXT NOT NULL,
    ash_level_at_time INTEGER,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_memories_player_npc ON npc_memories(player_id, npc_id);
CREATE INDEX IF NOT EXISTS idx_log_player_npc      ON dialogue_log(player_id, npc_id);
