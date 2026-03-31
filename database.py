import aiosqlite
import os
from config import DB_PATH

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id              INTEGER PRIMARY KEY DEFAULT 1,
                joined_at       TEXT DEFAULT (datetime('now')),
                streak          INTEGER DEFAULT 0,
                last_report     TEXT DEFAULT NULL,
                tasks_done      INTEGER DEFAULT 0,
                reads_done      INTEGER DEFAULT 0,
                last_photo_sent TEXT DEFAULT NULL
            )
        """)
        await db.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                title       TEXT NOT NULL,
                completed   INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,
                content_idx  INTEGER NOT NULL,
                created_at   TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.commit()


# ── PROFILE ──────────────────────────────────────────────────

async def get_profile() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM profile WHERE id = 1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}


async def update_streak(new_streak: int, today: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE profile SET streak=?, last_report=? WHERE id=1",
            (new_streak, today)
        )
        await db.commit()


async def increment_tasks_done():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE profile SET tasks_done = tasks_done + 1 WHERE id=1")
        await db.commit()


async def increment_reads():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE profile SET reads_done = reads_done + 1 WHERE id=1")
        await db.commit()


async def update_last_photo(ts: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE profile SET last_photo_sent=? WHERE id=1", (ts,))
        await db.commit()


# ── TASKS ─────────────────────────────────────────────────────

async def add_task(date: str, title: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tasks (date, title) VALUES (?, ?)", (date, title)
        )
        await db.commit()
        return cur.lastrowid


async def get_tasks(date: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE date=? ORDER BY id", (date,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def complete_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET completed=1 WHERE id=?", (task_id,))
        await db.commit()


async def delete_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()


async def delete_all_tasks(date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE date=?", (date,))
        await db.commit()


# ── ACTIONS ───────────────────────────────────────────────────

async def save_action(text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO actions (text) VALUES (?)", (text,))
        await db.commit()


async def get_last_actions(limit: int = 5) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ── READS ─────────────────────────────────────────────────────

async def save_read(content_type: str, content_idx: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reads (content_type, content_idx) VALUES (?, ?)",
            (content_type, content_idx)
        )
        await db.commit()


async def get_reads_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM reads") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0
