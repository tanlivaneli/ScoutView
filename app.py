import os
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
    season = 2024

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
    all_stats = []
    season = 2024
    for league_id, league_name in RAPID_LEAGUES.items():
        url = f"{RAPID_HOST}/players?id={player_id}&league={league_id}&season={season}"
        response = requests.get(url, headers=RAPID_HEADERS)
        data = response.json()
        if data.get("response"):
            all_stats.append(data["response"][0])

    if not all_stats:
        return render_template("home.html", leagues=LEAGUES)

    player_data = all_stats[0]["player"]
    return render_template("player_profile.html", player=player_data, stats=all_stats, leagues=LEAGUES)


if __name__ == "__main__":
    app.run(debug=True)