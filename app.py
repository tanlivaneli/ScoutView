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

if __name__ == "__main__":
    app.run(debug=True)