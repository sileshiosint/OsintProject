
from flask import Blueprint, render_template
import sqlite3
import json

history_bp = Blueprint("history", __name__)

@history_bp.route("/history")
def history():
    conn = sqlite3.connect("osint_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, query, search_type, platform, results, timestamp FROM searches ORDER BY timestamp DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()

    history_data = []
    for row in rows:
        history_data.append({
            "id": row[0],
            "query": row[1],
            "search_type": row[2],
            "platform": row[3],
            "results": json.loads(row[4]) if row[4] else [],
            "timestamp": row[5]
        })

    return render_template("history.html", history_data=history_data)
