"""
Data layer for NexLearn.
Mirrors the original PostgreSQL schema, swapped to SQLite for a free, zero-config demo.
"""

import sqlite3
from datetime import datetime, date

DB_PATH = "nexlearn.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS learners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            segment TEXT,
            course TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tutor_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id INTEGER,
            query TEXT,
            topic_guess TEXT,
            timestamp TEXT,
            FOREIGN KEY (learner_id) REFERENCES learners (id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id INTEGER,
            topic TEXT,
            difficulty TEXT,
            correct INTEGER,
            timestamp TEXT,
            FOREIGN KEY (learner_id) REFERENCES learners (id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id INTEGER,
            activity_date TEXT,
            FOREIGN KEY (learner_id) REFERENCES learners (id)
        )
    """)

    conn.commit()
    conn.close()


def get_or_create_learner(name, segment="Student", course="AWS Solutions Architect"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM learners WHERE name = ?", (name,))
    row = c.fetchone()
    if row:
        learner_id = row["id"]
    else:
        c.execute("INSERT INTO learners (name, segment, course) VALUES (?, ?, ?)",
                   (name, segment, course))
        conn.commit()
        learner_id = c.lastrowid
    conn.close()
    return learner_id


def log_tutor_query(learner_id, query, topic_guess):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tutor_queries (learner_id, query, topic_guess, timestamp) VALUES (?, ?, ?, ?)",
        (learner_id, query, topic_guess, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    log_activity(learner_id)


def log_quiz_attempt(learner_id, topic, difficulty, correct):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO quiz_attempts (learner_id, topic, difficulty, correct, timestamp) VALUES (?, ?, ?, ?, ?)",
        (learner_id, topic, difficulty, int(correct), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    log_activity(learner_id)


def log_activity(learner_id):
    today = date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM daily_activity WHERE learner_id = ? AND activity_date = ?",
        (learner_id, today)
    )
    if not c.fetchone():
        c.execute(
            "INSERT INTO daily_activity (learner_id, activity_date) VALUES (?, ?)",
            (learner_id, today)
        )
        conn.commit()
    conn.close()


def get_recent_quiz_attempts(learner_id, topic, limit=3):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT correct FROM quiz_attempts WHERE learner_id = ? AND topic = ? ORDER BY id DESC LIMIT ?",
        (learner_id, topic, limit)
    )
    rows = [r["correct"] for r in c.fetchall()]
    conn.close()
    return rows


def get_learner_quiz_history(learner_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT topic, difficulty, correct, timestamp FROM quiz_attempts WHERE learner_id = ? ORDER BY id",
        (learner_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def get_learner_activity_dates(learner_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT activity_date FROM daily_activity WHERE learner_id = ?", (learner_id,))
    rows = [r["activity_date"] for r in c.fetchall()]
    conn.close()
    return rows


def get_all_quiz_attempts():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT l.name, l.segment, q.topic, q.difficulty, q.correct, q.timestamp
        FROM quiz_attempts q JOIN learners l ON q.learner_id = l.id
        ORDER BY q.id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_tutor_queries():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT l.name, l.segment, t.query, t.topic_guess, t.timestamp
        FROM tutor_queries t JOIN learners l ON t.learner_id = l.id
        ORDER BY t.id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_learners():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, segment, course FROM learners")
    rows = c.fetchall()
    conn.close()
    return rows
