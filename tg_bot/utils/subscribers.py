import sqlite3
import os

DB_PATH = os.environ.get("SUBSCRIBERS_DB", "/data/subscribers.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)"
    )
    conn.commit()
    return conn


def add(chat_id: int) -> bool:
    with _conn() as conn:
        try:
            conn.execute("INSERT INTO subscribers VALUES (?)", (chat_id,))
            return True
        except sqlite3.IntegrityError:
            return False  # уже подписан


def remove(chat_id: int) -> bool:
    with _conn() as conn:
        rows = conn.execute(
            "DELETE FROM subscribers WHERE chat_id = ?", (chat_id,)
        ).rowcount
        return rows > 0


def all_ids() -> list[int]:
    with _conn() as conn:
        return [row[0] for row in conn.execute("SELECT chat_id FROM subscribers")]
