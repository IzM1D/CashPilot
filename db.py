import sqlite3

from app_config import DB_NAME


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()
    return conn, cur


def init_db():
    conn, cur = get_db()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    color TEXT DEFAULT '#1F1F1F'
                  );"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                    amount_cents INTEGER,
                    type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  );"""
    )
    conn.commit()
    cur.close()
    conn.close()


def get_categories():
    conn, cur = get_db()
    cur.execute("SELECT id, name, color FROM categories ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_category_from_db(category_id):
    conn, cur = get_db()
    cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    cur.close()
    conn.close()
