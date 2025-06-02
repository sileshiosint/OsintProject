
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "osint_data.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                search_type TEXT,
                platform TEXT,
                results TEXT,
                html TEXT,
                screenshot TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()

def log_result(query, search_type, platform, results, html=None, screenshot=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO searches (query, search_type, platform, results, html, screenshot, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            query,
            search_type,
            platform,
            json.dumps(results, ensure_ascii=False),
            html or "",
            screenshot or "",
            datetime.utcnow().isoformat()
        ))
        conn.commit()
