import os
import time
import unicodedata
from itertools import groupby
from flask import Flask, render_template, request, redirect, url_for
import requests
from dotenv import load_dotenv

load_dotenv()  # reads variables from a local .env file, if present

app = Flask(__name__)

API_KEY = os.environ["FOOTBALL_DATA_API_KEY"]
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

RAPID_KEY = os.environ["API_SPORTS_KEY"]
RAPID_HOST = "https://v3.football.api-sports.io"
RAPID_HEADERS = {"x-apisports-key": RAPID_KEY}

LEAGUES = {
    "PL": "Premier League",
    "BL1": "Bundesliga",
    "PD": "La Liga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "CL": "Champions League"
}

RAPID_LEAGUES = {
    39: "Premier League",
    78: "Bundesliga",
    140: "La Liga",
    135: "Serie A",
    61: "Ligue 1",
    2: "Champions League"
}

# Seasons in API-Sports are labeled by the year they start
# (e.g. the 2025/26 season is "2025"). The free API-Sports plan
# only has access to seasons 2022-2024, so this is capped at 2024
# until the plan is upgraded — bumping it further will return
# zero results with a "Free plans do not have access to this
# season" error.
CURRENT_SEASON = 2024

# Simple in-memory cache so repeat page loads (e.g. two people checking the
# same standings, or one person clicking back and forth) don't re-hit the
# external APIs every time. Storing this in a plain dict is fine for a
# single-process app like this one; it just resets whenever the app restarts.
_cache = {}


def cached_get(url, headers, ttl_seconds=300):
    """GET a URL and cache the parsed JSON for ttl_seconds. Team/league
    data barely changes minute to minute, so this cuts external API calls
    (and the odds of hitting a rate limit) dramatically for identical
    requests made close together. Error responses (e.g. rate limits) are
    never cached, so a transient failure doesn't stick around for the
    full TTL once the underlying issue clears."""
    now = time.time()
    entry = _cache.get(url)
    if entry and (now - entry["time"]) < ttl_seconds:
        return entry["data"]

    response = requests.get(url, headers=headers)
    data = response.json()
    if not data.get("errors"):
        _cache[url] = {"time": now, "data": data}
    return data

# Neither football-data.org nor API-Sports has a club trophies endpoint
# (only players/coaches, via API-Sports). This is a hand-maintained list
# of major honours for the biggest clubs across our 5 leagues, accurate
# as of mid-2026 — update the counts as seasons pass.
TEAM_HONOURS = {
    # ---- Premier League ----
    "liverpool": [
        {"name": "English League Titles", "count": 20},
        {"name": "FA Cup", "count": 8},
        {"name": "League Cup", "count": 10},
        {"name": "UEFA Champions League", "count": 6},
        {"name": "UEFA Europa League", "count": 3},
        {"name": "UEFA Super Cup", "count": 4},
        {"name": "FIFA Club World Cup", "count": 1},
    ],
    "arsenal": [
        {"name": "English League Titles", "count": 14},
        {"name": "FA Cup", "count": 14},
        {"name": "League Cup", "count": 2},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "Inter-Cities Fairs Cup", "count": 1},
    ],
    "nottingham forest": [
        {"name": "English League Titles", "count": 1},
        {"name": "League Cup", "count": 4},
        {"name": "European Cup", "count": 2},
        {"name": "European Super Cup", "count": 1},
    ],
    "chelsea": [
        {"name": "English League Titles", "count": 6},
        {"name": "FA Cup", "count": 8},
        {"name": "League Cup", "count": 5},
        {"name": "UEFA Champions League", "count": 2},
        {"name": "UEFA Europa League", "count": 2},
        {"name": "Cup Winners' Cup", "count": 2},
        {"name": "UEFA Conference League", "count": 1},
        {"name": "UEFA Super Cup", "count": 2},
        {"name": "FIFA Club World Cup", "count": 2},
    ],
    "manchester city": [
        {"name": "English League Titles", "count": 10},
        {"name": "FA Cup", "count": 8},
        {"name": "League Cup", "count": 9},
        {"name": "UEFA Champions League", "count": 1},
        {"name": "UEFA Super Cup", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "FIFA Club World Cup", "count": 1},
    ],
    "newcastle": [
        {"name": "English League Titles", "count": 4},
        {"name": "FA Cup", "count": 6},
        {"name": "League Cup", "count": 1},
        {"name": "Inter-Cities Fairs Cup", "count": 1},
    ],
    "aston villa": [
        {"name": "English League Titles", "count": 7},
        {"name": "FA Cup", "count": 7},
        {"name": "League Cup", "count": 5},
        {"name": "European Cup", "count": 1},
        {"name": "European Super Cup", "count": 1},
    ],
    "crystal palace": [
        {"name": "FA Cup", "count": 1},
    ],
    "everton": [
        {"name": "English League Titles", "count": 9},
        {"name": "FA Cup", "count": 5},
        {"name": "Cup Winners' Cup", "count": 1},
    ],
    "west ham": [
        {"name": "FA Cup", "count": 3},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "UEFA Conference League", "count": 1},
    ],
    "manchester united": [
        {"name": "English League Titles", "count": 20},
        {"name": "FA Cup", "count": 13},
        {"name": "League Cup", "count": 6},
        {"name": "UEFA Champions League", "count": 3},
        {"name": "UEFA Europa League", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "UEFA Super Cup", "count": 1},
        {"name": "FIFA Club World Cup", "count": 1},
    ],
    "wolverhampton": [
        {"name": "English League Titles", "count": 3},
        {"name": "FA Cup", "count": 4},
    ],
    "tottenham": [
        {"name": "English League Titles", "count": 2},
        {"name": "FA Cup", "count": 8},
        {"name": "League Cup", "count": 4},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "UEFA Europa League", "count": 3},
    ],
    "leeds united": [
        {"name": "English League Titles", "count": 3},
        {"name": "FA Cup", "count": 1},
    ],
    "burnley": [
        {"name": "English League Titles", "count": 2},
        {"name": "FA Cup", "count": 1},
    ],
    "sunderland": [
        {"name": "English League Titles", "count": 6},
        {"name": "FA Cup", "count": 2},
    ],

    # ---- Bundesliga ----
    "bayern": [
        {"name": "German League Titles", "count": 35},
        {"name": "DFB-Pokal", "count": 20},
        {"name": "DFL-Supercup", "count": 11},
        {"name": "UEFA Champions League", "count": 6},
        {"name": "UEFA Europa League", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "UEFA Super Cup", "count": 2},
        {"name": "FIFA Club World Cup", "count": 2},
        {"name": "Intercontinental Cup", "count": 2},
    ],
    "leverkusen": [
        {"name": "Bundesliga", "count": 1},
        {"name": "DFB-Pokal", "count": 2},
        {"name": "DFL-Supercup", "count": 1},
        {"name": "UEFA Europa League", "count": 1},
    ],
    "eintracht frankfurt": [
        {"name": "German League Titles", "count": 1},
        {"name": "DFB-Pokal", "count": 5},
        {"name": "UEFA Europa League", "count": 2},
    ],
    "borussia dortmund": [
        {"name": "German League Titles", "count": 8},
        {"name": "DFB-Pokal", "count": 5},
        {"name": "DFL-Supercup", "count": 6},
        {"name": "UEFA Champions League", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "Intercontinental Cup", "count": 1},
    ],
    "rb leipzig": [
        {"name": "DFB-Pokal", "count": 2},
        {"name": "DFL-Supercup", "count": 1},
    ],
    "werder bremen": [
        {"name": "German League Titles", "count": 4},
        {"name": "DFB-Pokal", "count": 6},
        {"name": "DFL-Ligapokal", "count": 1},
        {"name": "DFL-Supercup", "count": 3},
        {"name": "UEFA Europa League", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
    ],
    "vfb stuttgart": [
        {"name": "German League Titles", "count": 5},
        {"name": "DFB-Pokal", "count": 4},
        {"name": "DFL-Supercup", "count": 1},
    ],
    "monchengladbach": [
        {"name": "Bundesliga", "count": 5},
        {"name": "DFB-Pokal", "count": 3},
        {"name": "UEFA Europa League", "count": 2},
    ],
    "vfl wolfsburg": [
        {"name": "Bundesliga", "count": 1},
        {"name": "DFB-Pokal", "count": 1},
        {"name": "DFL-Supercup", "count": 1},
    ],
    "hamburger sv": [
        {"name": "German League Titles", "count": 6},
        {"name": "DFB-Pokal", "count": 3},
        {"name": "DFL-Ligapokal", "count": 2},
        {"name": "UEFA Champions League", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
    ],
    "koln": [
        {"name": "German League Titles", "count": 3},
        {"name": "DFB-Pokal", "count": 4},
    ],

    # ---- La Liga ----
    "barcelona": [
        {"name": "La Liga", "count": 29},
        {"name": "Copa del Rey", "count": 32},
        {"name": "Supercopa de España", "count": 16},
        {"name": "UEFA Champions League", "count": 5},
        {"name": "Cup Winners' Cup", "count": 4},
        {"name": "UEFA Super Cup", "count": 5},
        {"name": "FIFA Club World Cup", "count": 3},
    ],
    "real madrid": [
        {"name": "La Liga", "count": 36},
        {"name": "Copa del Rey", "count": 20},
        {"name": "Supercopa de España", "count": 13},
        {"name": "UEFA Champions League", "count": 15},
        {"name": "UEFA Europa League", "count": 2},
        {"name": "UEFA Super Cup", "count": 6},
        {"name": "FIFA Club World Cup", "count": 5},
        {"name": "Intercontinental Cup", "count": 3},
    ],
    "atletico madrid": [
        {"name": "La Liga", "count": 11},
        {"name": "Copa del Rey", "count": 10},
        {"name": "Supercopa de España", "count": 2},
        {"name": "UEFA Europa League", "count": 3},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "UEFA Super Cup", "count": 3},
        {"name": "Intercontinental Cup", "count": 1},
    ],
    "athletic": [
        {"name": "La Liga", "count": 8},
        {"name": "Copa del Rey", "count": 24},
        {"name": "Supercopa de España", "count": 3},
    ],
    "villarreal": [
        {"name": "UEFA Europa League", "count": 1},
    ],
    "real betis": [
        {"name": "La Liga", "count": 1},
        {"name": "Copa del Rey", "count": 3},
    ],
    "real sociedad": [
        {"name": "La Liga", "count": 2},
        {"name": "Copa del Rey", "count": 4},
        {"name": "Supercopa de España", "count": 1},
    ],
    "mallorca": [
        {"name": "Copa del Rey", "count": 1},
        {"name": "Supercopa de España", "count": 1},
    ],
    "sevilla": [
        {"name": "La Liga", "count": 1},
        {"name": "Copa del Rey", "count": 5},
        {"name": "Supercopa de España", "count": 1},
        {"name": "UEFA Europa League", "count": 7},
        {"name": "UEFA Super Cup", "count": 1},
    ],
    "valencia": [
        {"name": "La Liga", "count": 6},
        {"name": "Copa del Rey", "count": 8},
        {"name": "Supercopa de España", "count": 1},
        {"name": "UEFA Europa League", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "UEFA Super Cup", "count": 2},
    ],
    "espanyol": [
        {"name": "Copa del Rey", "count": 4},
    ],

    # ---- Serie A ----
    "napoli": [
        {"name": "Serie A", "count": 4},
        {"name": "Coppa Italia", "count": 6},
        {"name": "Supercoppa Italiana", "count": 3},
        {"name": "UEFA Europa League", "count": 1},
    ],
    "inter": [
        {"name": "Serie A", "count": 21},
        {"name": "Coppa Italia", "count": 10},
        {"name": "Supercoppa Italiana", "count": 8},
        {"name": "UEFA Champions League", "count": 3},
        {"name": "UEFA Europa League", "count": 3},
        {"name": "FIFA Club World Cup", "count": 1},
        {"name": "Intercontinental Cup", "count": 2},
    ],
    "atalanta": [
        {"name": "Coppa Italia", "count": 1},
        {"name": "UEFA Europa League", "count": 1},
    ],
    "juventus": [
        {"name": "Serie A", "count": 36},
        {"name": "Coppa Italia", "count": 15},
        {"name": "Supercoppa Italiana", "count": 9},
        {"name": "UEFA Champions League", "count": 2},
        {"name": "UEFA Europa League", "count": 3},
        {"name": "UEFA Super Cup", "count": 2},
        {"name": "Inter-Cities Fairs Cup", "count": 1},
        {"name": "Intercontinental Cup", "count": 2},
    ],
    "bologna": [
        {"name": "Serie A", "count": 7},
        {"name": "Coppa Italia", "count": 3},
    ],
    "roma": [
        {"name": "Serie A", "count": 3},
        {"name": "Coppa Italia", "count": 9},
        {"name": "Supercoppa Italiana", "count": 2},
        {"name": "UEFA Conference League", "count": 1},
        {"name": "Inter-Cities Fairs Cup", "count": 1},
    ],
    "lazio": [
        {"name": "Serie A", "count": 2},
        {"name": "Coppa Italia", "count": 7},
        {"name": "Supercoppa Italiana", "count": 5},
        {"name": "UEFA Super Cup", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
    ],
    "fiorentina": [
        {"name": "Serie A", "count": 2},
        {"name": "Coppa Italia", "count": 6},
        {"name": "Supercoppa Italiana", "count": 1},
        {"name": "Inter-Cities Fairs Cup", "count": 1},
    ],
    "ac milan": [
        {"name": "Serie A", "count": 19},
        {"name": "Coppa Italia", "count": 5},
        {"name": "Supercoppa Italiana", "count": 8},
        {"name": "UEFA Champions League", "count": 7},
        {"name": "UEFA Super Cup", "count": 5},
        {"name": "Cup Winners' Cup", "count": 2},
        {"name": "FIFA Club World Cup", "count": 1},
        {"name": "Intercontinental Cup", "count": 3},
    ],
    "torino": [
        {"name": "Serie A", "count": 7},
        {"name": "Coppa Italia", "count": 5},
    ],
    "genoa": [
        {"name": "Serie A", "count": 9},
        {"name": "Coppa Italia", "count": 1},
    ],
    "hellas verona": [
        {"name": "Serie A", "count": 1},
    ],
    "cagliari": [
        {"name": "Serie A", "count": 1},
    ],
    "parma": [
        {"name": "Coppa Italia", "count": 3},
        {"name": "Supercoppa Italiana", "count": 1},
        {"name": "UEFA Europa League", "count": 2},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "Inter-Cities Fairs Cup", "count": 1},
    ],

    # ---- Ligue 1 ----
    "paris saint-germain": [
        {"name": "Ligue 1", "count": 14},
        {"name": "Coupe de France", "count": 16},
        {"name": "Coupe de la Ligue", "count": 9},
        {"name": "Trophée des Champions", "count": 14},
        {"name": "UEFA Champions League", "count": 2},
        {"name": "UEFA Super Cup", "count": 1},
        {"name": "Cup Winners' Cup", "count": 1},
        {"name": "FIFA Intercontinental Cup", "count": 1},
    ],
    "marseille": [
        {"name": "Ligue 1", "count": 9},
        {"name": "Coupe de France", "count": 10},
        {"name": "UEFA Champions League", "count": 1},
    ],
    "monaco": [
        {"name": "Ligue 1", "count": 8},
        {"name": "Coupe de France", "count": 5},
    ],
    "lille": [
        {"name": "Ligue 1", "count": 6},
        {"name": "Coupe de France", "count": 6},
    ],
    "nice": [
        {"name": "Ligue 1", "count": 4},
        {"name": "Coupe de France", "count": 3},
    ],
    "lyon": [
        {"name": "Ligue 1", "count": 7},
        {"name": "Coupe de France", "count": 5},
    ],
    "lens": [
        {"name": "Ligue 1", "count": 1},
    ],
    "rennais": [
        {"name": "Coupe de France", "count": 3},
    ],
    "strasbourg": [
        {"name": "Ligue 1", "count": 1},
        {"name": "Coupe de France", "count": 3},
    ],
    "toulouse": [
        {"name": "Coupe de France", "count": 1},
    ],
    "nantes": [
        {"name": "Ligue 1", "count": 8},
        {"name": "Coupe de France", "count": 4},
    ],
    "auxerre": [
        {"name": "Ligue 1", "count": 1},
        {"name": "Coupe de France", "count": 4},
    ],
    "lorient": [
        {"name": "Coupe de France", "count": 1},
    ],
    "metz": [
        {"name": "Coupe de France", "count": 2},
    ],
}


def get_team_honours(team_name):
    """Fuzzy-match a football-data.org team name (e.g. 'Real Madrid CF')
    against our honours dataset keys (e.g. 'real madrid'). Accent-insensitive
    and matches on whole words so e.g. 'ac milan' won't also match 'Inter Milan'.
    If more than one key matches (e.g. a club whose full name includes another
    club's city, like 'RCD Espanyol de Barcelona'), we take whichever key's
    first word appears earliest in the name — the club's own identity leads
    the name, while a shared city name tends to trail as a suffix."""
    if not team_name:
        return None
    stripped = unicodedata.normalize("NFKD", team_name).encode("ascii", "ignore").decode()
    normalized = stripped.lower()

    best_key, best_position = None, None
    for key, honours in TEAM_HONOURS.items():
        words = key.split()
        if all(word in normalized for word in words):
            position = normalized.find(words[0])
            if best_position is None or position < best_position:
                best_key, best_position = key, position

    return TEAM_HONOURS[best_key] if best_key else None


def get_all_teams():
    teams = []
    for code in LEAGUES:
        url = f"{BASE_URL}/competitions/{code}/teams"
        data = cached_get(url, HEADERS, ttl_seconds=3600)  # team rosters barely change; cache an hour
        teams.extend(data.get("teams", []))
    return teams


@app.route("/")
def home():
    return render_template("home.html", leagues=LEAGUES)


@app.route("/standings")
def standings():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/standings"
    data = cached_get(url, HEADERS)
    table = data["standings"][0]["table"]
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("standings.html", table=table, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/results")
def results():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=FINISHED"
    data = cached_get(url, HEADERS)
    matches = data.get("matches", [])[-20:]
    matches.reverse()
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("results.html", matches=matches, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/fixtures")
def fixtures():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=SCHEDULED"
    data = cached_get(url, HEADERS)
    matches = data.get("matches", [])[:20]
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("fixtures.html", matches=matches, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/scorers")
def scorers():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/scorers?limit=20"
    data = cached_get(url, HEADERS)
    scorers_list = data.get("scorers", [])
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("scorers.html", scorers=scorers_list, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/assisters")
def assisters():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/scorers?limit=50"
    data = cached_get(url, HEADERS)
    all_players = data.get("scorers", [])
    assisters_list = sorted(
        [p for p in all_players if p.get("assists") and p["assists"] > 0],
        key=lambda x: x["assists"],
        reverse=True
    )[:20]
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("assisters.html", assisters=assisters_list, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/team/<int:team_id>")
def team(team_id):
    team_url = f"{BASE_URL}/teams/{team_id}"
    matches_url = f"{BASE_URL}/teams/{team_id}/matches?status=FINISHED&limit=5"
    next_url = f"{BASE_URL}/teams/{team_id}/matches?status=SCHEDULED&limit=1"

    team_data = cached_get(team_url, HEADERS)
    matches_data = cached_get(matches_url, HEADERS)
    next_data = cached_get(next_url, HEADERS)

    recent_matches = matches_data.get("matches", [])
    recent_matches.reverse()
    next_match = next_data.get("matches", [])
    next_match = next_match[0] if next_match else None

    team_honours = get_team_honours(team_data.get("name"))

    return render_template("team.html", team=team_data, recent_matches=recent_matches,
                           next_match=next_match, team_honours=team_honours)


@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return render_template("home.html", leagues=LEAGUES)
    all_teams = get_all_teams()
    matched = [t for t in all_teams if query in t["name"].lower()]
    seen = set()
    unique_teams = []
    for t in matched:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique_teams.append(t)
    return render_template("home.html", leagues=LEAGUES, teams=unique_teams, query=query)


@app.route("/player-search")
def player_search():
    query = request.args.get("q", "").strip()
    team_hint = request.args.get("team", "").strip()
    if not query:
        return render_template("home.html", leagues=LEAGUES)

    # strip accents (API-Sports search doesn't reliably match accented
    # characters, e.g. "Mbappé" vs "Mbappe")
    ascii_query = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode()
    normalized_query = ascii_query.lower()

    # search by surname alone first — API-Sports seems to match this more
    # reliably than a full "first last" search — and only fall back to
    # the full name if that comes up completely empty
    surname = ascii_query.split()[-1] if " " in ascii_query else ascii_query
    search_terms = [surname]
    if surname != ascii_query:
        search_terms.append(ascii_query)

    best_by_player = {}
    season = CURRENT_SEASON
    api_limited = False
    limit_message = ""

    for term in search_terms:
        if best_by_player or api_limited:
            break  # already found someone, or already hit a quota — stop calling the API
        for league_id in RAPID_LEAGUES:
            if api_limited:
                break
            url = f"{RAPID_HOST}/players?search={term}&league={league_id}&season={season}"
            data = cached_get(url, RAPID_HEADERS, ttl_seconds=600)
            errors = data.get("errors")
            if isinstance(errors, dict):
                if errors.get("rateLimit"):
                    api_limited = True
                    limit_message = "The player data API is temporarily rate-limited — wait a few seconds and try again."
                    continue
                if errors.get("requests"):
                    api_limited = True
                    limit_message = "The player data API's free daily request quota has been used up for today — try again after it resets (usually around midnight UTC)."
                    continue
            for item in data.get("response", []):
                pid = item["player"]["id"]
                stats = item.get("statistics") or [{}]
                appearances = (stats[0].get("games") or {}).get("appearences") or 0

                existing = best_by_player.get(pid)
                existing_appearances = 0
                if existing:
                    existing_stats = existing.get("statistics") or [{}]
                    existing_appearances = (existing_stats[0].get("games") or {}).get("appearences") or 0

                # keep whichever league shows more actual game time — a stale,
                # zero-appearance record from a former club shouldn't win over
                # the club a player has actually featured for this season
                if existing is None or appearances > existing_appearances:
                    best_by_player[pid] = item

    players = list(best_by_player.values())

    # prefer an exact (accent/case-insensitive) full-name match for the
    # auto-redirect. A surname search for "Kane" can turn up more than one
    # real player named Kane — filtering to whoever's full name exactly
    # matches what was searched (e.g. "Harry Kane") resolves that even
    # when the surname alone was ambiguous.
    exact_matches = [
        p for p in players
        if unicodedata.normalize("NFKD", p["player"]["name"]).encode("ascii", "ignore").decode().lower()
        == normalized_query
    ]
    if len(exact_matches) == 1:
        return redirect(url_for("player_profile", player_id=exact_matches[0]["player"]["id"]))

    # if even the exact name still matches more than one real player (e.g.
    # two different people both named "Vitinha"), use the team we already
    # knew them by — from wherever the link was clicked, like Top Scorers —
    # to pick the right one instead of showing a pick-one list
    if len(exact_matches) > 1 and team_hint:
        normalized_hint = unicodedata.normalize("NFKD", team_hint).encode("ascii", "ignore").decode().lower()
        team_matches = [
            p for p in exact_matches
            if (p.get("statistics") or [{}])[0].get("team", {}).get("name")
            and normalized_hint in unicodedata.normalize(
                "NFKD", p["statistics"][0]["team"]["name"]
            ).encode("ascii", "ignore").decode().lower()
        ]
        if len(team_matches) == 1:
            return redirect(url_for("player_profile", player_id=team_matches[0]["player"]["id"]))

    # otherwise, if the search resolved to exactly one player overall,
    # skip the results list and go straight to their profile
    if len(players) == 1:
        return redirect(url_for("player_profile", player_id=players[0]["player"]["id"]))

    return render_template("player_search.html", players=players, query=query, leagues=LEAGUES,
                           api_limited=api_limited, limit_message=limit_message)


@app.route("/player/<int:player_id>")
def player_profile(player_id):
    season = CURRENT_SEASON
    url = f"{RAPID_HOST}/players?id={player_id}&season={season}"
    data = cached_get(url, RAPID_HEADERS, ttl_seconds=600)

    errors = data.get("errors")
    if isinstance(errors, dict):
        if errors.get("rateLimit"):
            return render_template("home.html", leagues=LEAGUES,
                                   api_message="The player data API is temporarily rate-limited — wait a few seconds and try again.")
        if errors.get("requests"):
            return render_template("home.html", leagues=LEAGUES,
                                   api_message="The player data API's free daily request quota has been used up for today — try again after it resets (usually around midnight UTC).")

    if not data.get("response"):
        return render_template("home.html", leagues=LEAGUES)

    entry = data["response"][0]
    player_data = entry["player"]
    # reshape into the per-competition list the template expects
    all_stats = [{"statistics": [comp]} for comp in entry.get("statistics", [])]

    trophies_url = f"{RAPID_HOST}/trophies?player={player_id}"
    trophies_data = cached_get(trophies_url, RAPID_HEADERS, ttl_seconds=3600)  # trophies change rarely
    trophies = trophies_data.get("response", [])

    # the API sometimes returns the exact same trophy more than once
    seen = set()
    unique_trophies = []
    for t in trophies:
        key = (t.get("place"), t.get("league"), t.get("country"), t.get("season"))
        if key not in seen:
            seen.add(key)
            unique_trophies.append(t)

    # most recent season first within each group; trophies with no
    # season on record sink to the bottom of their group
    unique_trophies.sort(key=lambda t: t.get("season") or "", reverse=True)

    # group into Winner / 2nd Place / 3rd Place etc, winners shown first
    place_rank = {"Winner": 0, "2nd Place": 1, "Runner-up": 1, "3rd Place": 2}
    unique_trophies.sort(key=lambda t: place_rank.get(t.get("place", ""), 3))
    grouped_trophies = [(place, list(items)) for place, items in
                         groupby(unique_trophies, key=lambda t: t.get("place") or "Other")]

    return render_template("player_profile.html", player=player_data, stats=all_stats,
                           grouped_trophies=grouped_trophies, leagues=LEAGUES)


if __name__ == "__main__":
    app.run(debug=True)