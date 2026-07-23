import os
from itertools import groupby
from flask import Flask, render_template, request
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


def get_all_teams():
    teams = []
    for code in LEAGUES:
        url = f"{BASE_URL}/competitions/{code}/teams"
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        teams.extend(data.get("teams", []))
    return teams


@app.route("/")
def home():
    return render_template("home.html", leagues=LEAGUES)


@app.route("/standings")
def standings():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/standings"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    table = data["standings"][0]["table"]
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("standings.html", table=table, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/results")
def results():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=FINISHED"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    matches = data.get("matches", [])[-20:]
    matches.reverse()
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("results.html", matches=matches, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/fixtures")
def fixtures():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=SCHEDULED"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    matches = data.get("matches", [])[:20]
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("fixtures.html", matches=matches, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/scorers")
def scorers():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/scorers?limit=20"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    scorers_list = data.get("scorers", [])
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("scorers.html", scorers=scorers_list, leagues=LEAGUES, selected=league_code,
                           league_name=league_name)


@app.route("/assisters")
def assisters():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/scorers?limit=50"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
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

    team_data = requests.get(team_url, headers=HEADERS).json()
    matches_data = requests.get(matches_url, headers=HEADERS).json()
    next_data = requests.get(next_url, headers=HEADERS).json()

    recent_matches = matches_data.get("matches", [])
    recent_matches.reverse()
    next_match = next_data.get("matches", [])
    next_match = next_match[0] if next_match else None

    return render_template("team.html", team=team_data, recent_matches=recent_matches, next_match=next_match)


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
    if not query:
        return render_template("home.html", leagues=LEAGUES)

    players = []
    seen = set()
    season = CURRENT_SEASON

    for league_id in RAPID_LEAGUES:
        url = f"{RAPID_HOST}/players?search={query}&league={league_id}&season={season}"
        response = requests.get(url, headers=RAPID_HEADERS)
        data = response.json()
        for item in data.get("response", []):
            pid = item["player"]["id"]
            if pid not in seen:
                seen.add(pid)
                players.append(item)

    return render_template("player_search.html", players=players, query=query, leagues=LEAGUES)


@app.route("/player/<int:player_id>")
def player_profile(player_id):
    season = CURRENT_SEASON
    url = f"{RAPID_HOST}/players?id={player_id}&season={season}"
    response = requests.get(url, headers=RAPID_HEADERS)
    data = response.json()

    if not data.get("response"):
        return render_template("home.html", leagues=LEAGUES)

    entry = data["response"][0]
    player_data = entry["player"]
    # reshape into the per-competition list the template expects
    all_stats = [{"statistics": [comp]} for comp in entry.get("statistics", [])]

    trophies_url = f"{RAPID_HOST}/trophies?player={player_id}"
    trophies_response = requests.get(trophies_url, headers=RAPID_HEADERS)
    trophies = trophies_response.json().get("response", [])

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