import sqlite3
from datetime import datetime, timedelta, timezone

from config import DB_NAME


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn, conn.cursor()


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


def add_category(name: str, color: str):
    conn, cur = get_db()
    cur.execute("INSERT INTO categories (name, color) VALUES (?, ?)", (name, color))
    conn.commit()
    cur.close()
    conn.close()


def category_exists(name: str) -> bool:
    conn, cur = get_db()
    cur.execute("SELECT id FROM categories WHERE name = ?", (name,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def delete_category(category_id: int):
    conn, cur = get_db()
    cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    cur.close()
    conn.close()


def add_operation(category_id: int, amount_cents: int, op_type: str):
    conn, cur = get_db()
    current_time = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO operations(category_id, amount_cents, type, created_at) VALUES (?, ?, ?, ?)",
        (category_id, amount_cents, op_type, current_time),
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_operation(op_id: int):
    conn, cur = get_db()
    cur.execute("DELETE FROM operations WHERE id=?", (op_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_operations_by_category(category_id: int):
    conn, cur = get_db()
    cur.execute(
        """
        SELECT id, amount_cents, type, created_at
        FROM operations
        WHERE category_id=?
        ORDER BY created_at DESC
        """,
        (category_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_chart_rows():
    conn, cur = get_db()

    cur.execute(
        """
        SELECT c.name, c.color,
               COALESCE(SUM(CASE WHEN o.type='доход' THEN o.amount_cents ELSE 0 END), 0)
        FROM categories c
        LEFT JOIN operations o ON o.category_id = c.id
        GROUP BY c.id
        """
    )
    income_rows = [r for r in cur.fetchall() if r[2] > 0]

    cur.execute(
        """
        SELECT c.name, c.color,
               COALESCE(SUM(CASE WHEN o.type='расход' THEN -o.amount_cents ELSE 0 END), 0)
        FROM categories c
        LEFT JOIN operations o ON o.category_id = c.id
        GROUP BY c.id
        """
    )
    expense_rows = [r for r in cur.fetchall() if r[2] > 0]

    cur.close()
    conn.close()
    return income_rows, expense_rows
