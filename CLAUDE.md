# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ScoutView is a Flask web app showing live football (soccer) statistics — standings, results/fixtures, top scorers/assisters, team & player profiles, and a Champions League knockout bracket — for Europe's top 5 leagues plus the Champions League. It's a single-developer side project (see README.md for the full feature list and known limitations).

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
python app.py                # runs on http://127.0.0.1:5000
```

Requires a `.env` file (see `.env.example`) with `FOOTBALL_DATA_API_KEY` — the app will not start without it (`app.py` reads it via `os.environ[...]`, which raises on startup if missing). Get a free key from football-data.org.

There is no test suite, linter, or build step configured in this repo.

## Architecture

The entire backend is one file, `app.py` — a standard Flask app (`app = Flask(__name__)`) with route handlers, no blueprints. Templates are Jinja2 in `templates/`, styling/JS in `static/style.css` and `static/script.js` (vanilla, no frontend framework/build step — `base.html` is the shared layout all pages extend).

### Single upstream API: football-data.org

Every route (`BASE_URL`, `HEADERS`) hits football-data.org — standings, results, fixtures, top scorers/assisters, team rosters, and player search/profiles. The app previously also used API-Sports/API-Football for deeper per-player stats and trophy histories, but that key got suspended after deployment (its free tier isn't meant for public traffic), so that integration was removed entirely. Consequence: player profiles are bio-only (name, nationality, age, position, shirt number, current club) — football-data.org's free tier has no per-player stats endpoint, so `get_player_season_stats` only surfaces goals/assists for players who happen to rank on their competition's top-scorers/assisters leaderboard (already fetched for the Scorers/Assisters pages), and there's no player trophy data at all. See README.md's Known Limitations for the user-facing version of this trade-off.

`player_search` searches by substring across every squad returned by `get_all_teams()` (itself just `/competitions/{code}/teams`, which already includes each team's full squad — no separate lookup needed). A `team` query-param hint (passed from wherever the search link was clicked — scorers/assisters/squad pages) disambiguates same-name collisions via `teams_match`.

`significant_words` / `teams_match` (accent-stripping + stopword removal + word-set containment) were originally built to reconcile club names across two differently-formatted APIs; now single-API, they're used for `get_team_honours` name matching and the `player_search` team-hint disambiguation above.

### Caching

`cached_get()` is a simple in-memory dict cache (module-level `_cache`, keyed by URL, TTL per call site — team rosters cache for an hour, most other data for 5 minutes). It resets on process restart and is not safe to assume shared across multiple worker processes. Error responses are never cached, so a transient rate-limit doesn't stick around for the full TTL.

### Club trophies are hand-maintained data

football-data.org has no club-honours endpoint. `TEAM_HONOURS` in `app.py` is a manually researched dict of major honours for ~65 clubs, keyed by lowercase club name and matched fuzzily via `get_team_honours`. Updating it (new titles, new clubs) is manual, editorial work, not something to infer from an API response.

### Champions League knockout bracket

The `/knockouts` route pulls all CL matches, filters out group-stage rounds, then pairs two-legged ties by the unordered `{home_id, away_id}` team pair per stage and computes aggregate scores across both legs (`stage_sort_key` orders playoff → R16 → QF → SF → Final).

## Deployment

Deployed via `Procfile` (`gunicorn app:app`) — see the live demo link in README.md. `requirements.txt` is the full dependency list (Flask, requests, python-dotenv, gunicorn) — keep it in sync with anything actually imported in `app.py`.
