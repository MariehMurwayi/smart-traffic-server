import sqlite3, time
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
DB = "traffic.db"
ROADS = ["A", "B", "C", "D"]
EMERGENCY_GREEN = 10


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL, a INTEGER, b INTEGER, c INTEGER, d INTEGER,
        chosen TEXT, green INTEGER, emergency INTEGER DEFAULT 0)""")
    try:
        con.execute("ALTER TABLE readings ADD COLUMN emergency INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists
    con.commit()
    con.close()


def level(n):
    return "High" if n >= 4 else "Medium" if n >= 2 else "Low"


def make_plan(counts, emergency):
    if emergency in ROADS:
        return emergency, EMERGENCY_GREEN, 1
    chosen = max(ROADS, key=lambda r: counts[r])
    green = min(3 + counts[chosen], 10)
    return chosen, green, 0


def row_to_dict(row):
    counts = {"A": row["a"], "B": row["b"], "C": row["c"], "D": row["d"]}
    return {
        "time": time.strftime("%H:%M:%S", time.localtime(row["ts"])),
        "counts": counts,
        "levels": {r: level(counts[r]) for r in ROADS},
        "chosen": row["chosen"],
        "green": row["green"],
        "emergency": bool(row["emergency"]),
    }


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/api/counts", methods=["POST"])
def post_counts():
    data = request.get_json(force=True)
    counts = {r: int(data.get(r, 0)) for r in ROADS}
    emergency = str(data.get("emergency", "")).upper()[:1]
    chosen, green, is_emergency = make_plan(counts, emergency)
    con = db()
    con.execute(
        "INSERT INTO readings (ts,a,b,c,d,chosen,green,emergency) VALUES (?,?,?,?,?,?,?,?)",
        (time.time(), counts["A"], counts["B"], counts["C"], counts["D"],
         chosen, green, is_emergency))
    con.commit()
    con.close()
    return jsonify({"road": chosen, "green": green, "emergency": bool(is_emergency)})


@app.route("/api/latest")
def latest():
    con = db()
    row = con.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
    con.close()
    return jsonify(row_to_dict(row) if row else None)


@app.route("/api/history")
def history():
    con = db()
    rows = con.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 10").fetchall()
    con.close()
    return jsonify([row_to_dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)