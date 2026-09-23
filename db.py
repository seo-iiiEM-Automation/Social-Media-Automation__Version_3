"""SQLite storage for scheduled and published posts."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "posts.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,          -- 'instagram' or 'facebook'
            caption TEXT NOT NULL,
            image_url TEXT,
            scheduled_time TEXT,             -- ISO datetime, NULL = post now
            status TEXT NOT NULL DEFAULT 'pending',  -- pending, published, failed
            result_id TEXT,                  -- id returned by Meta after publish
            error TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_post(platform, caption, image_url, scheduled_time):
    conn = get_conn()
    conn.execute(
        """INSERT INTO posts (platform, caption, image_url, scheduled_time, status, created_at)
           VALUES (?, ?, ?, ?, 'pending', ?)""",
        (platform, caption, image_url, scheduled_time, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_pending_due(now_iso):
    """Posts that are pending and either due now or meant to post immediately."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM posts WHERE status = 'pending'
           AND (scheduled_time IS NULL OR scheduled_time <= ?)
           ORDER BY id ASC""",
        (now_iso,),
    ).fetchall()
    conn.close()
    return rows


def get_all_posts():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def mark_published(post_id, result_id):
    conn = get_conn()
    conn.execute(
        "UPDATE posts SET status = 'published', result_id = ? WHERE id = ?",
        (result_id, post_id),
    )
    conn.commit()
    conn.close()


def mark_failed(post_id, error):
    conn = get_conn()
    conn.execute(
        "UPDATE posts SET status = 'failed', error = ? WHERE id = ?",
        (str(error)[:500], post_id),
    )
    conn.commit()
    conn.close()


def delete_post(post_id):
    conn = get_conn()
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
