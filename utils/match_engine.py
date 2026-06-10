import random
from keyboards.keyboards import TACTICS_BONUS

OPPONENT_CLUBS = [
    {"name": "Реал Мадрид", "strength": 92},
    {"name": "Барселона", "strength": 88},
    {"name": "Манчестер Сіті", "strength": 91},
    {"name": "Арсенал", "strength": 85},
    {"name": "ПСЖ", "strength": 87},
    {"name": "Мілан", "strength": 82},
    {"name": "Динамо Київ", "strength": 72},
    {"name": "Шахтар", "strength": 75},
    {"name": "Ліверпуль", "strength": 89},
    {"name": "Атлетіко Мадрид", "strength": 84},
    {"name": "Ювентус", "strength": 83},
    {"name": "Баварія", "strength": 90},
    {"name": "Боруссія Дортмунд", "strength": 83},
    {"name": "Челсі", "strength": 82},
    {"name": "Інтер", "strength": 85},
]


def simulate_match(user_players: list, tactics: str, user_club_name: str) -> dict:
    if user_players:
        avg_rating = sum(p["rating"] for p in user_players) / len(user_players)
    else:
        avg_rating = 70

    tactic_bonus = TACTICS_BONUS.get(tactics, 3)
    random_factor = random.uniform(-8, 8)
    user_strength = avg_rating + tactic_bonus + random_factor

    opponent = random.choice(OPPONENT_CLUBS)
    while opponent["name"] == user_club_name:
        opponent = random.choice(OPPONENT_CLUBS)

    opp_strength = opponent["strength"] + random.uniform(-8, 8)
    strength_diff = user_strength - opp_strength

    if strength_diff > 10:
        user_goals = random.randint(2, 5)
        opp_goals = random.randint(0, 2)
    elif strength_diff > 3:
        user_goals = random.randint(1, 3)
        opp_goals = random.randint(0, 2)
    elif strength_diff > -3:
        user_goals = random.randint(0, 2)
        opp_goals = random.randint(0, 2)
    elif strength_diff > -10:
        user_goals = random.randint(0, 2)
        opp_goals = random.randint(1, 3)
    else:
        user_goals = random.randint(0, 2)
        opp_goals = random.randint(2, 5)

    if user_goals > opp_goals:
        result = "win"
        prize = random.randint(3_000_000, 8_000_000)
    elif user_goals == opp_goals:
        result = "draw"
        prize = random.randint(1_000_000, 3_000_000)
    else:
        result = "loss"
        prize = random.randint(500_000, 1_500_000)

    player_names = [p["name"] for p in user_players] if user_players else ["Невідомий"]
    opp_names = ["Лопез", "Маркес", "Сміт", "Мюллер", "Джонс", "Мартін", "Мартіна", "Браун", "Давід", "Лукас"]

    used_minutes = set()
    goal_events = []

    def unique_minute():
        m = random.randint(1, 90)
        attempts = 0
        while m in used_minutes and attempts < 20:
            m = random.randint(1, 90)
            attempts += 1
        used_minutes.add(m)
        return m

    for _ in range(user_goals):
        goal_events.append({"minute": unique_minute(), "scorer": random.choice(player_names), "team": "user"})
    for _ in range(opp_goals):
        goal_events.append({"minute": unique_minute(), "scorer": random.choice(opp_names), "team": "opponent"})

    goal_events.sort(key=lambda x: x["minute"])

    return {
        "opponent_name": opponent["name"],
        "user_goals": user_goals,
        "opp_goals": opp_goals,
        "result": result,
        "prize": prize,
        "goal_events": goal_events,
        "man_of_match": random.choice(user_players)["name"] if user_players else "Невідомий",
    }


def format_match_result(match_data: dict, user_club: str) -> str:
    result_emoji = {"win": "🏆", "draw": "🤝", "loss": "😞"}[match_data["result"]]
    result_text = {"win": "Перемога!", "draw": "Нічия", "loss": "Поразка"}[match_data["result"]]

    lines = [
        "⚽️ Товариський матч",
        "",
        f"{result_emoji} {result_text}",
        "",
        f"🏟 {user_club} {match_data['user_goals']}:{match_data['opp_goals']} {match_data['opponent_name']}",
        "",
    ]

    if match_data["goal_events"]:
        lines.append("⚽️ Голи:")
        for event in match_data["goal_events"]:
            icon = "🔵" if event["team"] == "user" else "🔴"
            lines.append(f"  {icon} {event['minute']}' {event['scorer']}")
        lines.append("")

    lines.append(f"⭐️ Гравець матчу: {match_data['man_of_match']}")
    lines.append(f"💰 Призові: €{match_data['prize']:,}")
    return "\n".join(lines)
