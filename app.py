import os
import time
import unicodedata
from datetime import date
from itertools import groupby
from flask import Flask, render_template, request, redirect, url_for
import requests
from dotenv import load_dotenv

load_dotenv()  # reads variables from a local .env file, if present

app = Flask(__name__)

API_KEY = os.environ["FOOTBALL_DATA_API_KEY"]
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

LEAGUES = {
    "PL": "Premier League",
    "BL1": "Bundesliga",
    "PD": "La Liga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "CL": "Champions League"
}

# Optional local-only enrichment. API-Sports' free tier gets suspended when
# used to power public traffic (that's what happened when this app was
# deployed with it), so it must never be set in a deployed environment —
# only in a local .env, never committed. Every use of RAPID_KEY below is
# guarded, so the app behaves identically to the deployed version whenever
# it's absent, which is always true on Render.
RAPID_KEY = os.environ.get("API_SPORTS_KEY")
RAPID_HOST = "https://v3.football.api-sports.io"
RAPID_HEADERS = {"x-apisports-key": RAPID_KEY}

RAPID_LEAGUES = {
    "PL": 39,
    "BL1": 78,
    "PD": 140,
    "SA": 135,
    "FL1": 61,
    "CL": 2,
}

# Seasons in API-Sports are labeled by the year they start (e.g. the 2025/26
# season is "2025"). The free plan only has access to seasons 2022-2024 —
# bumping this without a paid plan just returns zero results.
RAPID_SEASON = 2024

# Simple in-memory cache so repeat page loads (e.g. two people checking the
# same standings, or one person clicking back and forth) don't re-hit the
# external APIs every time. Storing this in a plain dict is fine for a
# single-process app like this one; it just resets whenever the app restarts.
_cache = {}


def cached_get(url, headers, ttl_seconds=300, is_error=None):
    """GET a URL and cache the parsed JSON for ttl_seconds. Team/league
    data barely changes minute to minute, so this cuts external API calls
    (and the odds of hitting a rate limit) dramatically for identical
    requests made close together. Non-200 responses (e.g. rate limits,
    which football-data.org returns as a 429 with no distinguishing key
    in the body) are never cached, so a transient failure doesn't stick
    around for the full TTL once the underlying issue clears. `is_error`
    is an optional extra check for APIs (like API-Sports) that report
    failures inside an HTTP-200 body instead of via status code — also
    skips caching when it returns True."""
    now = time.time()
    entry = _cache.get(url)
    if entry and (now - entry["time"]) < ttl_seconds:
        return entry["data"]

    # A network hiccup or rate limit on any one call (football-data.org's
    # free tier allows 10 requests/minute, easy to brush against when a
    # single page needs several calls) shouldn't take the whole page down
    # — degrade to an empty response, which every call site already
    # handles via .get(..., default). Failures are never cached (below),
    # so the next request past the rate-limit window recovers cleanly.
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
    except (requests.RequestException, ValueError):
        return {}

    if response.status_code == 200 and not (is_error and is_error(data)):
        _cache[url] = {"time": now, "data": data}
    return data

# football-data.org has no club trophies endpoint. This is a hand-maintained
# list of major honours for the biggest clubs across our 5 leagues, accurate
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


TEAM_NAME_STOPWORDS = {
    "fc", "cf", "afc", "ac", "sc", "ssc", "ud", "cd", "rcd", "ca", "cfc",
    "calcio", "club", "de", "the", "kv", "sv", "fk", "sk", "und", "1913",
    "1909", "1907", "1899", "1904", "04",
}


def strip_accents(text):
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()


def significant_words(name):
    """Break a club name down to its meaningful words: strip accents,
    treat hyphens/periods as spaces, and drop common filler words/suffixes
    (FC, CF, 'de', founding-year numbers, etc.) that don't reliably tell
    two differently-phrased versions of the same club name apart."""
    stripped = strip_accents(name).lower().replace("-", " ").replace(".", " ")
    return {w for w in stripped.split() if w not in TEAM_NAME_STOPWORDS}


def teams_match(name_a, name_b):
    """True if two club names likely refer to the same club, even when
    phrased differently (e.g. 'Atletico Madrid' vs 'Club Atlético de
    Madrid', or 'Paris Saint-Germain FC' vs 'Paris Saint Germain').
    Matches if the smaller set of significant words is fully contained
    in the larger one."""
    words_a, words_b = significant_words(name_a), significant_words(name_b)
    if not words_a or not words_b:
        return False
    smaller, larger = (words_a, words_b) if len(words_a) <= len(words_b) else (words_b, words_a)
    return smaller.issubset(larger)


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
    normalized = strip_accents(team_name).lower()

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


# Ordered hints for sorting knockout stages left-to-right. The Champions
# League switched formats in 2024/25 (league phase instead of groups, plus
# a knockout play-off round before the Round of 16), so rather than
# hardcoding exact stage names we sort by whichever of these keywords
# appears in the stage — this keeps working even if the exact stage name
# football-data.org uses for the play-off round differs from what's here.
KNOCKOUT_STAGE_ORDER_HINTS = ["PLAYOFF", "PLAY_OFF", "16", "QUARTER", "SEMI", "FINAL"]


def stage_sort_key(stage):
    stage_upper = stage.upper()
    for i, hint in enumerate(KNOCKOUT_STAGE_ORDER_HINTS):
        if hint in stage_upper:
            return i
    return len(KNOCKOUT_STAGE_ORDER_HINTS)


def stage_display_name(stage):
    return stage.replace("_", " ").title()


@app.route("/knockouts")
def knockouts():
    url = f"{BASE_URL}/competitions/CL/matches"
    data = cached_get(url, HEADERS, ttl_seconds=3600)
    all_matches = data.get("matches", [])

    # keep only knockout-stage matches — exclude the league/group phase,
    # which is already shown on the Standings page as a table
    knockout_matches = [
        m for m in all_matches
        if m.get("stage") and "GROUP" not in m["stage"].upper() and "LEAGUE" not in m["stage"].upper()
    ]

    stages = {}
    for m in knockout_matches:
        stages.setdefault(m["stage"], []).append(m)

    bracket = []
    for stage in sorted(stages.keys(), key=stage_sort_key):
        stage_matches = stages[stage]

        # pair up two-legged ties by the (unordered) set of the two teams
        ties = {}
        for m in stage_matches:
            key = tuple(sorted([m["homeTeam"]["id"], m["awayTeam"]["id"]]))
            ties.setdefault(key, []).append(m)

        tie_list = []
        for leg_matches in ties.values():
            leg_matches.sort(key=lambda x: x["utcDate"])
            team1 = leg_matches[0]["homeTeam"]
            team2 = leg_matches[0]["awayTeam"]

            legs = []
            agg1, agg2 = 0, 0
            any_finished = False
            for leg in leg_matches:
                h_score = leg["score"]["fullTime"]["home"]
                a_score = leg["score"]["fullTime"]["away"]
                if h_score is not None and a_score is not None:
                    any_finished = True
                    if leg["homeTeam"]["id"] == team1["id"]:
                        agg1 += h_score
                        agg2 += a_score
                    else:
                        agg1 += a_score
                        agg2 += h_score
                legs.append({"home_score": h_score, "away_score": a_score,
                            "home_is_team1": leg["homeTeam"]["id"] == team1["id"]})

            tie_list.append({
                "team1": team1,
                "team2": team2,
                "legs": legs,
                "agg1": agg1 if any_finished else None,
                "agg2": agg2 if any_finished else None,
                "two_legged": len(leg_matches) > 1,
            })

        bracket.append({"display_name": stage_display_name(stage), "ties": tie_list})

    return render_template("knockouts.html", bracket=bracket)


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

    normalized_query = strip_accents(query).lower()
    all_teams = get_all_teams()

    seen = set()
    matches = []
    for t in all_teams:
        for p in t.get("squad", []):
            if p["id"] in seen:
                continue
            if normalized_query in strip_accents(p["name"]).lower():
                seen.add(p["id"])
                matches.append({"player": p, "team": t})

    # if we know which club the link was clicked from, prefer that
    # candidate — narrows down same-name collisions (rare, but possible
    # for a common surname search)
    if team_hint:
        team_matches = [m for m in matches if teams_match(team_hint, m["team"]["name"])]
        if team_matches:
            matches = team_matches

    if len(matches) == 1:
        return redirect(url_for("player_profile", player_id=matches[0]["player"]["id"]))

    return render_template("player_search.html", players=matches, query=query, leagues=LEAGUES)


def find_club_team(player_id):
    """The persons/{id} endpoint's currentTeam can be a national team if
    the player was recently on international duty (football-data.org
    returns whichever squad they were most recently active with), so
    resolve their actual club from the same squad data player_search
    matches against instead of trusting it blindly. Also returns which
    of our 6 competition codes the player is actually registered under
    (a club's own runningCompetitions field isn't reliable for this —
    it can omit Champions League even for clubs actively playing in
    it), so get_player_season_stats only has to check those instead of
    blindly querying all 6 on every profile view — each one is a call
    against a free tier that's easy to rate-limit."""
    club_team = None
    codes = set()
    for code in LEAGUES:
        url = f"{BASE_URL}/competitions/{code}/teams"
        data = cached_get(url, HEADERS, ttl_seconds=3600)
        for t in data.get("teams", []):
            if any(p["id"] == player_id for p in t.get("squad", [])):
                club_team = club_team or t
                codes.add(code)
    return club_team, codes


def get_player_season_stats(player_id, competition_codes):
    """football-data.org's free tier has no per-player season-stats
    endpoint — the closest it offers is the scorers list per competition,
    which (despite the "top scorers" framing) returns every player with
    at least one goal when given a high enough limit, not just a small
    top-N. Returns one entry per competition the player has goals/assists
    in (e.g. a player can have separate domestic-league and Champions
    League tallies) rather than stopping at the first match. Players
    with zero goals this season (many defenders/keepers) still won't
    have a stats endpoint to pull from at all."""
    results = []
    for code in competition_codes:
        url = f"{BASE_URL}/competitions/{code}/scorers?limit=500"
        data = cached_get(url, HEADERS)
        for item in data.get("scorers", []):
            if item.get("player", {}).get("id") == player_id:
                results.append({
                    "competition": LEAGUES[code],
                    "goals": item.get("goals") or 0,
                    "assists": item.get("assists") or 0,
                    "penalties": item.get("penalties") or 0,
                    "played_matches": item.get("playedMatches") or 0,
                })
                break
    return results


def find_api_sports_player(name, club_name):
    """Optional local-only enrichment — see RAPID_KEY above; this is never
    active on the deployed site. Searches API-Sports by surname first (it
    matches more reliably there than a full "first last" search), falling
    back to the full name, then disambiguates same-name collisions using
    club_name via the same fuzzy teams_match already used for club
    honours (API-Sports and football-data.org don't always format club
    names identically)."""
    if not RAPID_KEY:
        return None

    ascii_name = strip_accents(name)
    surname = ascii_name.split()[-1] if " " in ascii_name else ascii_name
    search_terms = [surname]
    if surname != ascii_name:
        search_terms.append(ascii_name)

    is_api_sports_error = lambda d: d.get("errors")

    candidates = {}
    for term in search_terms:
        if candidates:
            break
        for league_id in RAPID_LEAGUES.values():
            url = f"{RAPID_HOST}/players?search={term}&league={league_id}&season={RAPID_SEASON}"
            data = cached_get(url, RAPID_HEADERS, ttl_seconds=3600, is_error=is_api_sports_error)
            if data.get("errors"):
                continue
            for item in data.get("response", []):
                candidates[item["player"]["id"]] = item

    matches = list(candidates.values())
    if not matches:
        return None

    if club_name:
        club_matches = [
            m for m in matches
            if (m.get("statistics") or [{}])[0].get("team", {}).get("name")
            and teams_match(club_name, m["statistics"][0]["team"]["name"])
        ]
        if club_matches:
            matches = club_matches

    return matches[0] if len(matches) == 1 else None


def get_api_sports_details(api_player_id):
    """Detailed per-competition stats and trophy history for a player
    already resolved via find_api_sports_player. Local-only, see
    RAPID_KEY above."""
    is_api_sports_error = lambda d: d.get("errors")

    url = f"{RAPID_HOST}/players?id={api_player_id}&season={RAPID_SEASON}"
    data = cached_get(url, RAPID_HEADERS, ttl_seconds=3600, is_error=is_api_sports_error)
    if data.get("errors") or not data.get("response"):
        return None

    entry = data["response"][0]
    stats = [{"statistics": [comp]} for comp in entry.get("statistics", [])]

    trophies_url = f"{RAPID_HOST}/trophies?player={api_player_id}"
    trophies_data = cached_get(trophies_url, RAPID_HEADERS, ttl_seconds=3600, is_error=is_api_sports_error)
    trophies = [] if trophies_data.get("errors") else trophies_data.get("response", [])

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

    return {
        "photo": entry.get("player", {}).get("photo"),
        "stats": stats,
        "grouped_trophies": grouped_trophies,
    }


@app.route("/player/<int:player_id>")
def player_profile(player_id):
    url = f"{BASE_URL}/persons/{player_id}"
    data = cached_get(url, HEADERS, ttl_seconds=3600)

    if not data.get("id"):
        return render_template("home.html", leagues=LEAGUES)

    age = None
    dob = data.get("dateOfBirth")
    if dob:
        birth = date.fromisoformat(dob[:10])
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    club_team, club_codes = find_club_team(player_id)
    season_stats = get_player_season_stats(player_id, club_codes)

    enrichment = None
    if RAPID_KEY:
        api_player = find_api_sports_player(data.get("name"), club_team.get("name") if club_team else None)
        if api_player:
            enrichment = get_api_sports_details(api_player["player"]["id"])

    return render_template("player_profile.html", player=data, age=age, club_team=club_team,
                           season_stats=season_stats, enrichment=enrichment, leagues=LEAGUES)


if __name__ == "__main__":
    app.run(debug=True)