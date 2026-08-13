# ⚽ ScoutView

Live football statistics across Europe's top leagues — built with Python, Flask, and two public football data APIs.

**[Live Demo](https://scoutview.onrender.com)**

---

## Features

- **Standings** — live league tables for the Premier League, Bundesliga, La Liga, Serie A, Ligue 1, and the Champions League
- **Results & Fixtures** — recent results and upcoming matches per league
- **Top Scorers & Top Assisters** — leaderboards with clickable player names linking straight to full profiles
- **Team profiles** — squad lists, recent form, next match, and a trophy cabinet of major honours
- **Player profiles** — season stats (goals, assists, cards, rating, etc.) and a full trophy history
- **Champions League knockout bracket** — playoff round through the final, with aggregate scores across two-legged ties
- **Team & player search** — search by name, with smart matching to resolve to the right profile even across ambiguous or differently-formatted names
- **Light/dark mode** — toggle in the nav, remembered across visits
- **Response caching** — reduces repeat API calls and keeps the app responsive

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML/Jinja2 templates, vanilla CSS and JavaScript (no frontend framework)
- **Data source:** [football-data.org](https://www.football-data.org/) — standings, results, fixtures, scorers, team data, and player search/profiles

## Running Locally

1. Clone the repo:
   ```bash
   git clone https://github.com/tanlivaneli/ScoutView.git
   cd ScoutView
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

3. Get a free API key from [football-data.org](https://www.football-data.org/client/register), then create a `.env` file in the project root (see `.env.example`):
   ```
   FOOTBALL_DATA_API_KEY=your_key_here
   ```

4. Run the app:
   ```bash
   python app.py
   ```
   Visit `http://127.0.0.1:5000`.

## Known Limitations

This project runs entirely on football-data.org's free-tier plan, which comes with a couple of real constraints worth knowing about:

- **Player profiles are bio-only** — name, nationality, age, position, shirt number, and current club. The free tier has no per-player stats endpoint (shots, passes, cards, rating), so a player's season goals/assists only show up if they rank high enough to appear on their competition's top scorers/assisters leaderboard.
- **No player trophy histories** — neither the free nor a paid football-data.org plan offers a player honours endpoint, so this isn't shown on player profiles (club trophies, below, are unaffected — that's separate hand-curated data).
- **Club trophy data is hand-curated**, not live — football-data.org has no club-honours endpoint, so major honours for ~65 clubs are manually researched and will need periodic updates as seasons conclude.

## Roadmap

This is an active side project, not a finished product — a few things planned for the future:

- Expand club trophy coverage beyond the current ~65 major clubs
- Find a reliable, ToS-compliant source for deeper player stats and trophy histories
- Add match-level statistics (possession, shots, cards) if a suitable data source is found
- General UI polish and performance improvements as I keep learning

## Credits

Built by [Tan Livaneli](https://github.com/tanlivaneli). Data powered by [football-data.org](https://www.football-data.org/) and [API-Sports](https://www.api-football.com/).