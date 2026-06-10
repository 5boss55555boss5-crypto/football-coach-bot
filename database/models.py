import aiosqlite

DB_PATH = "football_coach.db"


def get_db():
    return aiosqlite.connect(DB_PATH)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                budget INTEGER NOT NULL,
                team_strength INTEGER NOT NULL,
                country TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                rating INTEGER NOT NULL,
                value INTEGER NOT NULL,
                salary INTEGER NOT NULL,
                club_id INTEGER,
                is_free_agent INTEGER DEFAULT 0,
                FOREIGN KEY (club_id) REFERENCES clubs(id)
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                club_id INTEGER,
                budget INTEGER DEFAULT 0,
                tactics TEXT DEFAULT 'tactic_balanced',
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                coach_rating INTEGER DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (club_id) REFERENCES clubs(id)
            );

            CREATE TABLE IF NOT EXISTS user_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (player_id) REFERENCES players(id)
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_club TEXT NOT NULL,
                opponent_club TEXT NOT NULL,
                user_score INTEGER NOT NULL,
                opponent_score INTEGER NOT NULL,
                result TEXT NOT NULL,
                prize_money INTEGER NOT NULL,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        await db.commit()
