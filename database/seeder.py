import aiosqlite
from data.seed_data import CLUBS, PLAYERS

DB_PATH = "football_coach.db"


async def seed_database():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM clubs") as cursor:
            count = (await cursor.fetchone())[0]
            if count > 0:
                return

        for club in CLUBS:
            await db.execute(
                "INSERT INTO clubs (id, name, budget, team_strength, country) VALUES (?, ?, ?, ?, ?)",
                (club["id"], club["name"], club["budget"], club["team_strength"], club["country"])
            )

        for player in PLAYERS:
            is_free = player.get("is_free_agent", 0)
            await db.execute(
                "INSERT INTO players (name, position, rating, value, salary, club_id, is_free_agent) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (player["name"], player["position"], player["rating"], player["value"],
                 player["salary"], player.get("club_id"), is_free)
            )

        await db.commit()
        print("✅ База даних заповнена початковими даними")
