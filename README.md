# Realm of Ashes — AI NPC Demo

A browser-playable 2D RPG tech demo showcasing an **AI-driven NPC dialogue system** with persistent memory and ash-level reactivity. Every NPC remembers the player across sessions and adapts tone, refusal behavior, and perception based on the player's corruption (Ash Level 0–10).

This is an intentionally small, polished demo — a single village with 8 NPCs and 10 hardcoded ash events — designed as a portfolio piece, not a full game.

## Status

- **Phase 1 — Backend Core: complete.** FastAPI + SQLite + Anthropic Claude API. Milestone test passes: Kael the blacksmith shifts tone dramatically between ash=2 and ash=7, and references earlier conversations across sessions.
- Phase 2 — Phaser frontend skeleton: planned.
- Phase 3 — Frontend/backend integration: planned.
- Phase 4 — Ash mechanics (10 events, threshold effects, hidden NPCs): planned.
- Phase 5 — Polish, assets, deploy: planned.

## Architecture

- **Backend:** Python 3.12 · FastAPI 0.111 · aiosqlite (WAL mode) · Anthropic SDK 0.28. Deployed on Railway.
- **Frontend (planned):** Phaser 3.80 via CDN, vanilla ES6. Deployed on GitHub Pages.
- **Models:** `claude-haiku-4-5` for standard NPCs + memory extraction. `claude-sonnet-4-6` for Elder Voss and The Presence.
- **Memory model:** 10 general + 3 emotional memories per (player × NPC), FIFO eviction. Memory extraction runs as a FastAPI `BackgroundTask` after each dialogue response.

## API endpoints

```
POST   /api/player/init                 Create a new player with initial ash level
POST   /api/dialogue                    Send dialogue to an NPC, receive reply
POST   /api/ash/update                  Apply an ash-level change (e.g. ash_event)
GET    /api/player/{id}/memories/{npc}  Inspect what an NPC remembers about a player
DELETE /api/player/{id}/reset           Wipe a player's state (dev helper)
GET    /health                          Railway healthcheck
```

## Local development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or conda
pip install -r requirements.txt
cp .env.example .env                                # then fill in ANTHROPIC_API_KEY
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API docs.

## Milestone test (terminal)

```bash
cd backend
python test_terminal.py
```

Prints five dialogue exchanges with Kael — three at ash=2, two at ash=7 — and dumps the final memory set. Expected: clear tone shift, preserved emotional memory ("Player lost brother in the waste"), and cross-session recall.

## Deployment

- **Backend → Railway.** Root directory: `backend/`. Service reads `ANTHROPIC_API_KEY`, `DATABASE_PATH` (point at a persistent volume, e.g. `/data/roa.db`), and `ALLOWED_ORIGINS` (comma-separated frontend origins).
- **Frontend → GitHub Pages** (once Phase 2 lands).

## Project spec

The authoritative design document is `Realm of Ashes – AI NPC Demo.pdf` in this folder. All implementation decisions trace back to it.

## License

Personal portfolio project. Not currently licensed for redistribution.
