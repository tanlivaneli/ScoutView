from flask import Flask, render_template, request
import requests

app = Flask(__name__)

API_KEY = "1bc6cda045d54c4393a00dab3bc11cf8"
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
    return render_template("standings.html", table=table, leagues=LEAGUES, selected=league_code, league_name=league_name)

@app.route("/results")
def results():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=FINISHED"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    matches = data.get("matches", [])[-20:]
    matches.reverse()
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("results.html", matches=matches, leagues=LEAGUES, selected=league_code, league_name=league_name)

@app.route("/fixtures")
def fixtures():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/matches?status=SCHEDULED"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    matches = data.get("matches", [])[:20]
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("fixtures.html", matches=matches, leagues=LEAGUES, selected=league_code, league_name=league_name)

@app.route("/scorers")
def scorers():
    league_code = request.args.get("league", "PL")
    url = f"{BASE_URL}/competitions/{league_code}/scorers?limit=20"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    scorers_list = data.get("scorers", [])
    league_name = LEAGUES.get(league_code, "Unknown League")
    return render_template("scorers.html", scorers=scorers_list, leagues=LEAGUES, selected=league_code, league_name=league_name)

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
    return render_template("assisters.html", assisters=assisters_list, leagues=LEAGUES, selected=league_code, league_name=league_name)

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

if __name__ == "__main__":
    app.run(debug=True)