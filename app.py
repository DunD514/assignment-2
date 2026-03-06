from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import pandas as pd
import psycopg2
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Use environment variable on Render (never hardcode credentials!)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ipl_auction_db_cusl_user:cGeaQvFN6VJj2h5mS2TNPyR6XxVXEOQG@dpg-d6l7i2s50q8c73bo4b6g-a/ipl_auction_db_cusl"
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Initialize DB (run once at startup)
conn = get_db_connection()
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS players(
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE,
    price INTEGER,
    runs INTEGER,
    wickets INTEGER,
    matches INTEGER,
    role TEXT
)
""")
conn.commit()

# Import from Excel only if table is empty
cur.execute("SELECT COUNT(*) FROM players")
if cur.fetchone()[0] == 0:
    df = pd.read_excel("players.xlsx")
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO players(name, price, runs, wickets, matches, role)
            VALUES(%s, %s, %s, %s, %s, %s)
        """, (
            row["name"], row["base_price"], row["runs"],
            row["wickets"], row["matches"], row["role"]
        ))
    conn.commit()

cur.close()
conn.close()

def get_players():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price, runs, wickets, matches, role FROM players")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    players = {}
    for r in rows:
        players[r[0]] = {
            "price": r[1],
            "runs": r[2],
            "wickets": r[3],
            "matches": r[4],
            "role": r[5]
        }
    return players


html = """ ... (your HTML is perfectly fine - no changes needed) ... """


@app.route("/")
def home():
    players = get_players()
    return render_template_string(html, players=players)


@socketio.on("place_bid")
def handle_bid(data):
    player = data["player"]
    try:
        bid = int(data["bid"])
    except ValueError:
        emit("error", {"msg": "Invalid bid amount"})
        return

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT price FROM players WHERE name=%s", (player,))
    current = cur.fetchone()[0]

    if bid > current:
        cur.execute("UPDATE players SET price=%s WHERE name=%s", (bid, player))
        conn.commit()

        emit("price_update", {"player": player, "price": bid}, broadcast=True)
    else:
        emit("error", {"msg": "Bid must be higher than current price"})

    cur.close()
    conn.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
