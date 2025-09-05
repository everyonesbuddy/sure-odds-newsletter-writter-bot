import requests
import random
import time
from datetime import datetime, timedelta
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configs
SCOPES = ['https://www.googleapis.com/auth/documents']
DOCUMENT_TITLE = "Sure-Odds Daily Newsletter"

# Leagues & Emojis
leagues = {
    "basketball_wnba": "WNBA Basketball",
    "soccer_epl": "English Premier League",
    # "basketball_nba": "NBA Basketball",
    "americanfootball_nfl": "NFL Football",
    "baseball_mlb": "MLB Baseball",
    "hockey_nhl": "NHL Hockey",
    "soccer_spain_la_liga": "La Liga",
}

sport_emojis = {
    "basketball_wnba": "🏀",
    "soccer_epl": "⚽",
    # "basketball_nba": "🏀",
    "americanfootball_nfl": "🏈",
    "baseball_mlb": "⚾",
    "hockey_nhl": "🏒",
    "soccer_spain_la_liga": "⚽",
}

# === Contest Date Helpers ===
today = datetime.now()

# Start/end of week
start_of_week = today - timedelta(days=today.weekday() + 1)  # Sunday
end_of_week = start_of_week + timedelta(days=6)  # Saturday
start_of_week_str = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
end_of_week_str = end_of_week.replace(hour=23, minute=59, second=59, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

# Start/end of month
start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
next_month = start_of_month.replace(day=28) + timedelta(days=4)  # always next month
end_of_month = next_month - timedelta(days=next_month.day)
end_of_month = end_of_month.replace(hour=23, minute=59, second=59, microsecond=0)
start_of_month_str = start_of_month.strftime("%Y-%m-%d %H:%M:%S")
end_of_month_str = end_of_month.strftime("%Y-%m-%d %H:%M:%S")

# === Contest Configuration (same as Twitter bot) ===
contests = [
    {
        "title": "Weekly Multi Sport Streak",
        "prize": "$100 Amazon Gift Card",
        "duration": "weekly",
        "start_date": start_of_week_str,
        "end_date": end_of_week_str,
        "contest_format": "streak",
        "win_conditions": "Hit 6 correct picks in a row",
        "url": "https://sure-odds.com/"
    },
    {
        "title": "Season Long EPL Pick'em",
        "prize": "$1000 cash prize",
        "duration": "season-long",
        "start_date": "2025-08-15 00:00:00",
        "end_date": "2026-05-24 23:59:59",
        "contest_format": "pickem",
        "win_conditions": "Have the most correct picks this EPL season",
        "url": "https://sure-odds.com/"
    },
    {
        "title": "Monthly Multi Sport Streak",
        "prize": "$300 Amazon Gift Card",
        "duration": "monthly",
        "start_date": start_of_month_str,
        "end_date": end_of_month_str,
        "contest_format": "streak",
        "win_conditions": "Hit 12 correct picks in a row",
        "url": "https://sure-odds.com/"
    }
]

# === Newsletter Templates (aligned with Twitter bot) ===
newsletter_templates = {
    "streak": [
        "🎯 **{win_conditions}** in our **{title}** and win **{prize}**!\n\nIt's FREE to enter. Contest runs {start_date} to {end_date}.",
        "🔥 **{title}** is live!\n\n{win_conditions}. FREE entry!\nContest ends {end_date}.",
        "🏆 Can you achieve it? {win_conditions} in this {duration} streak contest.\n\nWin **{prize}**. FREE entry. Contest closes {end_date}."
    ],
    "pickem": [
        "🎯 **{win_conditions}** in our **{title}** and win **{prize}**!\n\nIt's FREE to enter. Contest runs {start_date} to {end_date}.",
        "🔥 **{title}** is live!\n\n{win_conditions}. FREE entry!\nContest ends {end_date}.",
        "🏆 Be the top predictor! {win_conditions} in this {duration} Pick'em.\n\nWin **{prize}**. FREE entry. Contest closes {end_date}."
    ]
}

# === Subject Line Templates ===
subject_line_templates = [
    "🎯 Win prizes in Sure-Odds free-to-play sports contests",
    "💸 Free sports contests with real prizes – play at Sure-Odds",
    "🏆 Join Sure-Odds: Free-to-play contests, real rewards",
    "🔥 Predict, play, and win prizes at Sure-Odds",
    "📅 Weekly & monthly sports contests – free entry, real prizes"
]

def get_subject_line():
    return random.choice(subject_line_templates)

# === Sports Data Helpers ===
def get_featured_matchup_moneyline():
    league_key = random.choice(list(leagues.keys()))
    league_name = leagues[league_key]
    emoji = sport_emojis.get(league_key, "")

    url = (
        f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/"
        f"?apiKey=402f2e4bba957e5e98c7e1a178393c8c&regions=us&markets=h2h&oddsFormat=american&bookmakers=draftkings"
    )
    res = requests.get(url)
    if res.status_code != 200:
        return "⚠️ Could not fetch moneyline odds today."

    games = res.json()
    if not games:
        return "⚠️ No matchups available with moneylines."

    game = random.choice(games)
    home = game.get("home_team")
    away = game.get("away_team")

    try:
        outcomes = game["bookmakers"][0]["markets"][0]["outcomes"]
        moneylines = {o["name"]: o["price"] for o in outcomes}

        home_ml = moneylines.get(home, "?")
        away_ml = moneylines.get(away, "?")
        draw_ml = moneylines.get("Draw")  # only exists for sports like soccer

        odds_text = f"- {home}: {home_ml}\n"
        if draw_ml is not None:
            odds_text += f"- Draw: {draw_ml}\n"
        odds_text += f"- {away}: {away_ml}"

        return f"""{emoji} **{home} vs {away}** – *{league_name}*

💵 **Moneyline Odds:**
{odds_text}
"""
    except:
        return "⚠️ Could not parse moneyline data properly."


# === Newsletter Builder ===
def build_newsletter(subject_line):
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    contest = random.choice(contests)

    # Format dates
    start_date_obj = datetime.strptime(contest["start_date"], "%Y-%m-%d %H:%M:%S")
    end_date_obj = datetime.strptime(contest["end_date"], "%Y-%m-%d %H:%M:%S")
    formatted_start_date = start_date_obj.strftime("%Y-%m-%d")
    formatted_end_date = end_date_obj.strftime("%Y-%m-%d")

    # Contest intro (aligned with Twitter templates)
    format_templates = newsletter_templates.get(contest["contest_format"], newsletter_templates["streak"])
    intro = random.choice(format_templates).format(
        title=contest["title"],
        prize=contest["prize"],
        duration=contest["duration"],
        win_conditions=contest["win_conditions"],
        start_date=formatted_start_date,
        end_date=formatted_end_date
    )

    # Newsletter content
    featured = get_featured_matchup_moneyline()

    return f"""📬 **Suggested Subject Line:** _{subject_line}_

# 📅 {date_str} | Sure-Odds Contests

---

{intro}

🔗 [Enter here to play free →]({contest['url']})

---

## 🎯 Featured Matchup (Moneyline Odds)
{featured}
"""

# === Google Docs Push ===
def push_to_google_doc(markdown_text):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('docs', 'v1', credentials=creds)
    doc = service.documents().create(body={"title": DOCUMENT_TITLE}).execute()
    doc_id = doc['documentId']

    service.documents().batchUpdate(documentId=doc_id, body={
        'requests': [{
            'insertText': {
                'location': {'index': 1},
                'text': markdown_text
            }
        }]
    }).execute()

    print(f"✅ Newsletter sent to Google Docs: https://docs.google.com/document/d/{doc_id}/edit")

# === Main Runner ===
def post_daily_newsletter():
    try:
        print("🚀 Building newsletter...")
        subject_line = get_subject_line()
        newsletter = build_newsletter(subject_line)
        push_to_google_doc(newsletter)
        print(f"📬 Suggested Subject: \"{subject_line}\"")
    except Exception as e:
        print(f"❌ Error: {e}")

# Run once
post_daily_newsletter()
