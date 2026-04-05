import os
import json
import requests
from datetime import datetime, timedelta, timezone
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("PANDASCORE_TOKEN")

BASE_URL = "https://api.pandascore.co"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader("templates"))


def get_date_range(day_offset: int):
    today = datetime.now(timezone.utc).date()
    target = today + timedelta(days=day_offset)
    return f"{target}T00:00:00Z", f"{target}T23:59:59Z"


def fetch_matches(day_offset: int):
    start, end = get_date_range(day_offset)
    params = {
        "range[scheduled_at]": f"{start},{end}",
        "per_page": 50,
        "sort": "scheduled_at",
    }

    if day_offset == -1:
        url = f"{BASE_URL}/matches/past"
    elif day_offset == 1:
        url = f"{BASE_URL}/matches/upcoming"
    else:
        url = f"{BASE_URL}/matches"

    resp = requests.get(url, headers=HEADERS, params=params)

    # Для дебага — покажет что вернул API
    if not resp.ok:
        print(f"❌ Ошибка {resp.status_code}: {resp.text}")
        return []

    raw = resp.json()


    matches = []
    for m in raw:
        team1 = m.get("opponents", [{}])[0].get("opponent", {}).get("name", "TBD") if len(
            m.get("opponents", [])) > 0 else "TBD"
        team2 = m.get("opponents", [{}])[1].get("opponent", {}).get("name", "TBD") if len(
            m.get("opponents", [])) > 1 else "TBD"

        scheduled = m.get("scheduled_at", "")
        if scheduled:
            dt = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M UTC")
        else:
            time_str = "—"

        status_map = {
            "running": "🔴 Live",
            "finished": "✅ Завершён",
            "not_started": "🕐 Ожидается",
        }

        matches.append({
            "team1": team1,
            "team2": team2,
            "game": m.get("videogame", {}).get("name", "Esports"),
            "time": time_str,
            "status": status_map.get(m.get("status", ""), m.get("status", "")),
            "league": m.get("league", {}).get("name", ""),
        })

    return matches


def build_schema(matches, page_label):
    events = []
    for m in matches:
        events.append({
            "@type": "SportsEvent",
            "name": f"{m['team1']} vs {m['team2']}",
            "sport": m["game"],
            "competitor": [
                {"@type": "SportsTeam", "name": m["team1"]},
                {"@type": "SportsTeam", "name": m["team2"]},
            ],
        })
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"Киберспортивные матчи — {page_label}",
        "itemListElement": events,
    }, ensure_ascii=False, indent=2)


def generate_page(filename, day_offset, title, description, keywords, heading, active, page_label):
    matches = fetch_matches(day_offset)
    schema = build_schema(matches, page_label)
    template = env.get_template("matches.html")
    html = template.render(
        title=title,
        description=description,
        keywords=keywords,
        schema=schema,
        heading=heading,
        matches=matches,
        active=active,
    )
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {filename} — {len(matches)} матчей")


if __name__ == "__main__":
    generate_page(
        filename="yesterday.html",
        day_offset=-1,
        title="Киберспортивные матчи вчера | EsportsMatches",
        description="Результаты вчерашних киберспортивных матчей по CS2, Dota 2, LoL и другим дисциплинам.",
        keywords="киберспорт, матчи вчера, результаты, CS2, Dota 2, LoL",
        heading="Матчи за вчерашний день",
        active="yesterday",
        page_label="Вчера",
    )
    generate_page(
        filename="today.html",
        day_offset=0,
        title="Киберспортивные матчи сегодня | EsportsMatches",
        description="Актуальное расписание и результаты сегодняшних киберспортивных матчей.",
        keywords="киберспорт, матчи сегодня, расписание, CS2, Dota 2, LoL",
        heading="Матчи за сегодняшний день",
        active="today",
        page_label="Сегодня",
    )
    generate_page(
        filename="tomorrow.html",
        day_offset=1,
        title="Киберспортивные матчи завтра | EsportsMatches",
        description="Расписание киберспортивных матчей на завтра — CS2, Dota 2, LoL и другие.",
        keywords="киберспорт, матчи завтра, анонс, CS2, Dota 2, LoL",
        heading="Матчи на завтра",
        active="tomorrow",
        page_label="Завтра",
    )
    print("\n🎉 Готово! Файлы в папке output/")