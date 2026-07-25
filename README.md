# ⚽ ScoutView

Live football statistics across Europe's top leagues — built with Python, Flask, and two public football data APIs.

**[Live Demo](#)** *(add your Render URL here once deployed)*

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
- **Data sources:**
  - [football-data.org](https://www.football-data.org/) — standings, results, fixtures, scorers, team data
  - [API-Sports (API-Football)](https://www.api-football.com/) — player stats, player/team trophies

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

3. Get free API keys from [football-data.org](https://www.football-data.org/client/register) and [API-Sports](https://dashboard.api-football.com/register), then create a `.env` file in the project root (see `.env.example`):
   ```
   FOOTBALL_DATA_API_KEY=your_key_here
   API_SPORTS_KEY=your_key_here
   ```

4. Run the app:
   ```bash
   python app.py
   ```
   Visit `http://127.0.0.1:5000`.

## Known Limitations

This project runs entirely on free-tier API plans, which come with a couple of real constraints worth knowing about:

- **Player season data is capped at 2024** — API-Sports' free plan only includes seasons 2022–2024, so player stats and search reflect that season rather than the current one. Team standings/results/fixtures are unaffected, since those come from football-data.org and are always current.
- **API-Sports allows 100 requests/day** on the free tier, shared across all visitors. The app caches responses to minimize this, and shows a clear message if the daily quota is reached rather than failing silently.
- **Club trophy data is hand-curated**, not live — neither API offers a club honours endpoint, so major honours for ~65 clubs are manually researched and will need periodic updates as seasons conclude. Player trophies, by contrast, are pulled live.

## Credits

Built by [Tan Livaneli](https://github.com/tanlivaneli). Data powered by [football-data.org](https://www.football-data.org/) and [API-Sports](https://www.api-football.com/).