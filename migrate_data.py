import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "football_coach.db")
SQL_FILE = os.path.join(os.path.dirname(__file__), "migrate_data.sql")


def main():
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    db = sqlite3.connect(DB_PATH)
    db.executescript(sql)
    db.commit()
    db.close()
    print(f"Migration applied to {DB_PATH}")


if __name__ == "__main__":
    main()
