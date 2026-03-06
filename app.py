import eventlet
eventlet.monkey_patch()
import random  # For additional made-up stats if needed

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
socketio = SocketIO(app, cors_allowed_origins="*")

# Database URL
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ipl_auction_db_cusl_user:cGeaQvFN6VJj2h5mS2TNPyR6XxVXEOQG@dpg-d6l7i2s50q8c73bo4b6g-a/ipl_auction_db_cusl"
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Real IPL Players Data (researched from ESPNcricinfo, IPLT20.com, Wikipedia - career stats as of 2025)
PLAYERS_DATA = [
    {"name": "Virat Kohli", "base_price": 20000000, "runs": 8661, "wickets": 0, "matches": 267, "role": "Batsman"},
    {"name": "Rohit Sharma", "base_price": 20000000, "runs": 7046, "wickets": 17, "matches": 272, "role": "Batsman"},
    {"name": "Shikhar Dhawan", "base_price": 20000000, "runs": 6769, "wickets": 11, "matches": 222, "role": "Batsman"},
    {"name": "David Warner", "base_price": 20000000, "runs": 6565, "wickets": 6, "matches": 184, "role": "Batsman"},
    {"name": "Suresh Raina", "base_price": 20000000, "runs": 5528, "wickets": 26, "matches": 205, "role": "All-rounder"},
    {"name": "MS Dhoni", "base_price": 20000000, "runs": 5439, "wickets": 0, "matches": 278, "role": "Wicketkeeper"},
    {"name": "KL Rahul", "base_price": 20000000, "runs": 5222, "wickets": 0, "matches": 145, "role": "Wicketkeeper"},
    {"name": "Suryakumar Yadav", "base_price": 20000000, "runs": 3429, "wickets": 1, "matches": 143, "role": "Batsman"},
    {"name": "Jasprit Bumrah", "base_price": 20000000, "runs": 243, "wickets": 183, "matches": 145, "role": "Bowler"},
    {"name": "Yuzvendra Chahal", "base_price": 20000000, "runs": 212, "wickets": 221, "matches": 174, "role": "Bowler"},
    {"name": "Sunil Narine", "base_price": 20000000, "runs": 1027, "wickets": 192, "matches": 189, "role": "All-rounder"},
    {"name": "Piyush Chawla", "base_price": 20000000, "runs": 454, "wickets": 192, "matches": 192, "role": "Bowler"},
    {"name": "Ravichandran Ashwin", "base_price": 20000000, "runs": 840, "wickets": 187, "matches": 221, "role": "All-rounder"},
    {"name": "Bhuvneshwar Kumar", "base_price": 20000000, "runs": 608, "wickets": 198, "matches": 190, "role": "Bowler"},
    {"name": "Andre Russell", "base_price": 20000000, "runs": 2420, "wickets": 127, "matches": 150, "role": "All-rounder"},
    {"name": "Rashid Khan", "base_price": 20000000, "runs": 324, "wickets": 154, "matches": 121, "role": "Bowler"},
    {"name": "Rishabh Pant", "base_price": 20000000, "runs": 2461, "wickets": 0, "matches": 111, "role": "Wicketkeeper"},
    {"name": "Hardik Pandya", "base_price": 20000000, "runs": 1954, "wickets": 64, "matches": 123, "role": "All-rounder"}
]

# Initialize DB Tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Players table (existing)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
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

    # Import real players data if empty
    cur.execute("SELECT COUNT(*) FROM players")
    if cur.fetchone()[0] == 0:
        for row in PLAYERS_DATA:
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

init_db()

def get_players():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price, runs, wickets, matches, role FROM players ORDER BY name")
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

def generate_made_up_stats(role):
    """Generate random but realistic made-up stats based on role"""
    stats = {
        "batting_average": random.randint(25, 55),
        "strike_rate": random.randint(110, 165),
        "bowling_economy": round(random.uniform(5.5, 9.5), 2),
        "best_batting_score": random.randint(50, 200),
        "best_bowling_figures": f"{random.randint(3, 8)}/{random.randint(20, 50)}",
        "fielding_catches": random.randint(10, 50),
        "recent_form": random.choice(["Excellent", "Good", "Average", "Poor"]),
        "auction_notes": random.choice([
            "Explosive opener with power-hitting ability.",
            "Consistent middle-order anchor.",
            "Death-over specialist bowler.",
            "Versatile all-rounder who can bat and bowl.",
            "Reliable wicketkeeper with safe hands."
        ])
    }
    if role == "Bowler":
        stats["batting_average"] = random.randint(5, 15)
        stats["strike_rate"] = random.randint(80, 120)
    return stats

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template_string(SIGNUP_HTML)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, generate_password_hash(password))
            )
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash('Username or email already exists.', 'error')
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    return render_template_string(SIGNUP_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('auction'))
        flash('Invalid username or password.', 'error')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/auction')
@login_required
def auction():
    players = get_players()
    return render_template_string(AUCTION_HTML, players=players, username=session['username'])

@app.route('/player/<name>')
@login_required
def player_detail(name):
    players = get_players()
    if name not in players:
        flash('Player not found.', 'error')
        return redirect(url_for('auction'))
    
    player = players[name]
    made_up_stats = generate_made_up_stats(player['role'])
    
    return render_template_string(PLAYER_DETAIL_HTML, 
                                  name=name, 
                                  player=player, 
                                  stats=made_up_stats, 
                                  username=session['username'])

# SocketIO Events
@socketio.on("place_bid")
def handle_bid(data):
    if 'user_id' not in session:
        emit("error", {"msg": "Please log in to bid."})
        return

    player = data["player"]
    try:
        bid = int(data["bid"])
    except ValueError:
        emit("error", {"msg": "Invalid bid amount"})
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT price FROM players WHERE name=%s", (player,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        emit("error", {"msg": "Player not found."})
        return

    current = result[0]

    if bid > current:
        cur.execute("UPDATE players SET price=%s WHERE name=%s", (bid, player))
        conn.commit()

        # Broadcast update with bidder info
        emit("price_update", {
            "player": player,
            "price": bid,
            "bidder": session['username']
        }, broadcast=True)
    else:
        emit("error", {"msg": "Bid must be higher than current price"})

    cur.close()
    conn.close()

# HTML Templates (unchanged from previous)
SIGNUP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Up - IPL Auction</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .auth-card { background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); padding: 2rem; max-width: 400px; width: 100%; }
        .btn-custom { background: linear-gradient(45deg, #22c55e, #16a34a); border: none; border-radius: 10px; padding: 12px 24px; font-weight: bold; transition: transform 0.2s; }
        .btn-custom:hover { transform: scale(1.05); }
        .form-control:focus { border-color: #22c55e; box-shadow: 0 0 0 0.2rem rgba(34, 197, 94, 0.25); }
        .flash { margin-bottom: 1rem; border-radius: 10px; padding: 10px; }
        .flash.success { background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; }
        .flash.error { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; }
        .flash.warning { background: rgba(251, 191, 36, 0.2); border: 1px solid #fbbf24; }
        .flash.info { background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="text-center mb-4">
            <i class="fas fa-user-plus fa-3x text-success mb-3"></i>
            <h2>Sign Up for IPL Auction</h2>
            <p class="text-muted">Join the excitement!</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label"><i class="fas fa-user"></i> Username</label>
                <input type="text" class="form-control" name="username" required>
            </div>
            <div class="mb-3">
                <label class="form-label"><i class="fas fa-envelope"></i> Email</label>
                <input type="email" class="form-control" name="email" required>
            </div>
            <div class="mb-3">
                <label class="form-label"><i class="fas fa-lock"></i> Password</label>
                <input type="password" class="form-control" name="password" required minlength="6">
            </div>
            <button type="submit" class="btn btn-custom w-100"><i class="fas fa-sign-in-alt"></i> Sign Up</button>
        </form>
        <div class="text-center mt-3">
            <p>Already have an account? <a href="{{ url_for('login') }}" class="text-success">Log In</a></p>
        </div>
    </div>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log In - IPL Auction</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .auth-card { background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); padding: 2rem; max-width: 400px; width: 100%; }
        .btn-custom { background: linear-gradient(45deg, #22c55e, #16a34a); border: none; border-radius: 10px; padding: 12px 24px; font-weight: bold; transition: transform 0.2s; }
        .btn-custom:hover { transform: scale(1.05); }
        .form-control:focus { border-color: #22c55e; box-shadow: 0 0 0 0.2rem rgba(34, 197, 94, 0.25); }
        .flash { margin-bottom: 1rem; border-radius: 10px; padding: 10px; }
        .flash.success { background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; }
        .flash.error { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; }
        .flash.warning { background: rgba(251, 191, 36, 0.2); border: 1px solid #fbbf24; }
        .flash.info { background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="text-center mb-4">
            <i class="fas fa-sign-in-alt fa-3x text-success mb-3"></i>
            <h2>Log In to IPL Auction</h2>
            <p class="text-muted">Welcome back!</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label"><i class="fas fa-user"></i> Username</label>
                <input type="text" class="form-control" name="username" required>
            </div>
            <div class="mb-3">
                <label class="form-label"><i class="fas fa-lock"></i> Password</label>
                <input type="password" class="form-control" name="password" required>
            </div>
            <button type="submit" class="btn btn-custom w-100"><i class="fas fa-sign-in-alt"></i> Log In</button>
        </form>
        <div class="text-center mt-3">
            <p>No account? <a href="{{ url_for('signup') }}" class="text-success">Sign Up</a></p>
        </div>
    </div>
</body>
</html>
"""

AUCTION_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPL Live Auction</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        :root { --primary: #22c55e; --secondary: #16a34a; --bg: #0f172a; --card: #1e293b; --hover: #334155; }
        body { background: linear-gradient(135deg, var(--bg) 0%, var(--card) 100%); color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .header { background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(20px); border-bottom: 1px solid #334155; padding: 1rem 0; }
        .user-info { color: var(--primary); font-weight: bold; }
        .logout-btn { background: none; border: 1px solid #ef4444; color: #ef4444; border-radius: 20px; padding: 5px 15px; transition: all 0.3s; }
        .logout-btn:hover { background: #ef4444; color: white; transform: translateY(-2px); }
        .auction-card { background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); overflow: hidden; }
        .player-row { transition: all 0.3s ease; cursor: pointer; border-left: 4px solid transparent; }
        .player-row:hover { background: var(--hover); transform: translateX(5px); border-left-color: var(--primary); }
        .player-name { color: var(--primary); text-decoration: none; }
        .player-name:hover { text-decoration: underline; }
        .price { font-weight: bold; color: var(--primary); font-size: 1.2rem; transition: all 0.3s; }
        .price.animate { animation: pulse 0.5s ease-in-out; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.2); color: #84cc16; } 100% { transform: scale(1); } }
        .stats-badge { background: rgba(34, 197, 94, 0.2); color: var(--primary); border: 1px solid var(--primary); border-radius: 15px; padding: 2px 8px; font-size: 0.8rem; }
        .bid-btn { background: linear-gradient(45deg, var(--primary), var(--secondary)); border: none; border-radius: 25px; padding: 8px 16px; transition: all 0.3s; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3); }
        .bid-btn:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4); }
        .bid-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .status { transition: all 0.3s; }
        .status.new-bid { animation: flash 1s infinite; color: #f59e0b; }
        @keyframes flash { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0.5; } }
        .search-input, .filter-select { border-radius: 25px; border: 2px solid #475569; background: #334155; color: white; padding: 10px 15px; }
        .search-input:focus, .filter-select:focus { border-color: var(--primary); box-shadow: 0 0 0 0.2rem rgba(34, 197, 94, 0.25); }
        .live-indicator { position: fixed; top: 20px; right: 20px; background: var(--primary); color: white; padding: 10px; border-radius: 50px; font-weight: bold; animation: pulse 2s infinite; z-index: 1000; }
        .role-icon { margin-right: 5px; }
        .role-batsman { color: #3b82f6; } .role-bowler { color: #ef4444; } .role-allrounder { color: #f59e0b; } .role-wicketkeeper { color: #8b5cf6; }
        table { border-radius: 15px; overflow: hidden; }
        thead th { background: #334155; border: none; }
        tbody tr { border-bottom: 1px solid #475569; }
        .modal-content { background: var(--card); color: white; border: none; border-radius: 20px; }
        .modal-header { border-bottom: 1px solid #475569; }
        .flash { position: fixed; top: 80px; left: 50%; transform: translateX(-50%); z-index: 1001; border-radius: 10px; padding: 10px 20px; min-width: 300px; }
        .flash.success { background: rgba(34, 197, 94, 0.9); } .flash.error { background: rgba(239, 68, 68, 0.9); } .flash.warning { background: rgba(251, 191, 36, 0.9); } .flash.info { background: rgba(59, 130, 246, 0.9); }
    </style>
</head>
<body>
    <div class="live-indicator"><i class="fas fa-broadcast-tower"></i> LIVE AUCTION</div>
    
    <div class="header">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <h1 class="mb-0"><i class="fas fa-trophy"></i> IPL Live Auction</h1>
                <div class="user-info d-flex align-items-center">
                    <span>Welcome, {{ username }}! </span>
                    <a href="{{ url_for('logout') }}" class="logout-btn ms-3"><i class="fas fa-sign-out-alt"></i> Logout</a>
                </div>
            </div>
        </div>
    </div>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row mb-4">
            <div class="col-md-4">
                <input type="text" class="form-control search-input" id="search" placeholder="🔍 Search Players...">
            </div>
            <div class="col-md-4">
                <select class="form-select filter-select" id="roleFilter">
                    <option value="all">All Roles</option>
                    <option value="Batsman">🦾 Batsman</option>
                    <option value="Bowler">🏏 Bowler</option>
                    <option value="All-rounder">⚡ All-rounder</option>
                    <option value="Wicketkeeper">🧤 Wicketkeeper</option>
                </select>
            </div>
            <div class="col-md-4 text-end">
                <button class="btn btn-outline-light" onclick="refreshPlayers()"><i class="fas fa-sync-alt"></i> Refresh</button>
            </div>
        </div>

        <div class="auction-card p-4">
            <div class="table-responsive">
                <table class="table table-dark table-hover mb-0">
                    <thead>
                        <tr>
                            <th><i class="fas fa-user"></i> Player</th>
                            <th><i class="fas fa-briefcase"></i> Role</th>
                            <th><i class="fas fa-chart-line"></i> Runs</th>
                            <th><i class="fas fa-bullseye"></i> Wickets</th>
                            <th><i class="fas fa-calendar"></i> Matches</th>
                            <th><i class="fas fa-rupee-sign"></i> Current Price</th>
                            <th><i class="fas fa-info-circle"></i> Status</th>
                            <th><i class="fas fa-gavel"></i> Actions</th>
                        </tr>
                    </thead>
                    <tbody id="playerTable">
                        {% for p in players %}
                        <tr class="player-row" data-role="{{players[p]['role']}}" data-name="{{p}}">
                            <td><a href="{{ url_for('player_detail', name=p) }}" class="player-name"><strong>{{p}}</strong></a></td>
                            <td><i class="fas role-icon role-{{players[p]['role'].lower().replace(' ', '').replace('-', '')}}"></i>{{players[p]["role"]}}</td>
                            <td><span class="stats-badge">{{players[p]["runs"]}}</span></td>
                            <td><span class="stats-badge">{{players[p]["wickets"]}}</span></td>
                            <td><span class="stats-badge">{{players[p]["matches"]}}</span></td>
                            <td class="price" id="price_{{p}}">₹{{players[p]["price"]}}</td>
                            <td class="status" id="status_{{p}}"><span class="badge bg-secondary">Waiting</span></td>
                            <td>
                                <button class="bid-btn" onclick="openBidModal('{{p}}', {{players[p]["price"]}})" title="Place Bid">
                                    <i class="fas fa-gavel"></i> Bid Now
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Bid Modal -->
    <div class="modal fade" id="bidModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-gavel"></i> Place Bid for <span id="modalPlayer"></span></h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Current Price: <strong id="modalCurrentPrice"></strong></p>
                    <div class="mb-3">
                        <label class="form-label">Your Bid (must be higher):</label>
                        <input type="number" class="form-control" id="bidAmount" min="1" step="1" required>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-success" onclick="submitBid()"><i class="fas fa-hammer"></i> Submit Bid</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const socket = io({transports:["websocket","polling"]});
        const modal = new bootstrap.Modal(document.getElementById('bidModal'));
        let currentPlayer = '';

        function openBidModal(player, currentPrice) {
            currentPlayer = player;
            document.getElementById('modalPlayer').textContent = player;
            document.getElementById('modalCurrentPrice').textContent = '₹' + currentPrice;
            const bidInput = document.getElementById('bidAmount');
            bidInput.value = currentPrice + 100; // Suggest next bid
            bidInput.min = currentPrice + 1;
            modal.show();
        }

        function submitBid() {
            const bidValue = document.getElementById('bidAmount').value;
            if (!bidValue) {
                alert('Please enter a bid amount.');
                return;
            }
            const bid = parseInt(bidValue);
            const current = parseInt(document.getElementById('modalCurrentPrice').textContent.replace('₹', ''));
            if (bid <= current) {
                alert('Bid must be higher than current price!');
                return;
            }
            socket.emit("place_bid", {player: currentPlayer, bid: bid});
            modal.hide();
            document.getElementById('bidAmount').value = ''; // Clear input
        }

        socket.on("price_update", function(data) {
            const priceCell = document.getElementById('price_' + data.player);
            const statusCell = document.getElementById('status_' + data.player);
            if (priceCell) {
                priceCell.innerText = '₹' + data.price;
                priceCell.classList.add('animate');
                setTimeout(() => priceCell.classList.remove('animate'), 500);
            }
            if (statusCell) {
                statusCell.innerHTML = `<span class="badge bg-warning new-bid">🔥 Bidded by ${data.bidder}!</span>`;
                setTimeout(() => {
                    statusCell.innerHTML = '<span class="badge bg-secondary">Waiting</span>';
                }, 3000);
            }
            // Play sound
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhB4H/9u2Y2Q==');
            audio.play().catch(() => {});
        });

        socket.on("error", function(data) {
            alert(data.msg);
        });

        // Fixed Filter (with console logging for debug)
        let searchTimeout;
        document.getElementById("search").addEventListener("input", function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(filterTable, 300);
        });

        document.getElementById("roleFilter").addEventListener("change", filterTable);

        function filterTable() {
            const filterText = document.getElementById("search").value.toLowerCase();
            const selectedRole = document.getElementById("roleFilter").value;
            const rows = document.querySelectorAll("#playerTable tr");
            let visibleCount = 0;
            rows.forEach(function(row) {
                const playerName = row.dataset.name.toLowerCase();
                const playerRole = row.dataset.role;
                const matchesSearch = playerName.includes(filterText);
                const matchesRole = selectedRole === 'all' || playerRole === selectedRole;
                const shouldShow = matchesSearch && matchesRole;
                row.style.display = shouldShow ? '' : 'none';
                if (shouldShow) visibleCount++;
            });
            console.log(`Filtered to ${visibleCount} players`); // Debug log
        }

        function refreshPlayers() {
            location.reload();
        }

        // Auto-hide flashes
        setTimeout(() => {
            document.querySelectorAll('.flash').forEach(el => {
                el.style.transition = 'opacity 0.5s';
                el.style.opacity = '0';
            });
        }, 5000);

        // Confetti on high bid
        function celebrateBid() {
            for (let i = 0; i < 50; i++) {
                const confetti = document.createElement('div');
                confetti.style.cssText = `
                    position: fixed; left: ${Math.random() * 100}vw; top: -10px; 
                    width: 10px; height: 10px; background: hsl(${Math.random() * 360}, 100%, 50%);
                    pointer-events: none; z-index: 9999; animation: fall 3s linear forwards;
                `;
                document.body.appendChild(confetti);
                setTimeout(() => confetti.remove(), 3000);
            }
        }
        const fallStyle = document.createElement('style');
        fallStyle.textContent = '@keyframes fall { to { transform: translateY(100vh) rotate(360deg); opacity: 0; } }';
        document.head.appendChild(fallStyle);

        let lastPrices = {}; // Track prices for big jump detection
        socket.on("price_update", function(data) {
            // ... existing code above ...
            const oldPrice = lastPrices[data.player] || parseInt(document.getElementById('price_' + data.player)?.textContent.replace('₹', '') || 0);
            lastPrices[data.player] = data.price;
            if (data.price > oldPrice * 1.5) celebrateBid();
        });

        // Initial filter call (in case of pre-filled search)
        filterTable();
    </script>
</body>
</html>
"""

PLAYER_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ name }} - IPL Auction</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root { --primary: #22c55e; --bg: #0f172a; --card: #1e293b; }
        body { background: linear-gradient(135deg, var(--bg) 0%, var(--card) 100%); color: white; font-family: 'Segoe UI', sans-serif; }
        .header { background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(20px); padding: 1rem 0; border-bottom: 1px solid #334155; }
        .player-card { background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); margin: 2rem 0; }
        .stat-badge { background: rgba(34, 197, 94, 0.2); color: var(--primary); border: 1px solid var(--primary); border-radius: 10px; padding: 5px 10px; margin: 5px; display: inline-block; }
        .bid-section { background: var(--primary); color: white; border-radius: 15px; padding: 1.5rem; text-align: center; }
        .back-btn { background: none; border: 1px solid #475569; color: white; border-radius: 20px; padding: 10px 20px; transition: all 0.3s; }
        .back-btn:hover { background: #475569; transform: translateY(-2px); }
        .role-icon-large { font-size: 3rem; color: var(--primary); }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <a href="{{ url_for('auction') }}" class="back-btn"><i class="fas fa-arrow-left"></i> Back to Auction</a>
                <h1><i class="fas fa-user"></i> Player Details</h1>
                <div class="user-info">
                    <span>Welcome, {{ username }}!</span>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="player-card p-4">
            <div class="row">
                <div class="col-md-4 text-center">
                    <div class="role-icon-large">
                        {% if player.role == 'Batsman' %}<i class="fas fa-baseball-ball"></i>
                        {% elif player.role == 'Bowler' %}<i class="fas fa-bowling-ball"></i>
                        {% elif player.role == 'All-rounder' %}<i class="fas fa-handshake"></i>
                        {% else %}<i class="fas fa-gloves"></i>{% endif %}
                    </div>
                    <h2 class="mt-3">{{ name }}</h2>
                    <p class="text-muted">{{ player.role }}</p>
                </div>
                <div class="col-md-8">
                    <h4>Core Stats</h4>
                    <div class="row">
                        <div class="col-md-3"><span class="stat-badge">Runs: {{ player.runs }}</span></div>
                        <div class="col-md-3"><span class="stat-badge">Wickets: {{ player.wickets }}</span></div>
                        <div class="col-md-3"><span class="stat-badge">Matches: {{ player.matches }}</span></div>
                        <div class="col-md-3"><span class="stat-badge">Price: ₹{{ player.price }}</span></div>
                    </div>
                </div>
            </div>
            <hr>
            <h4>Made-Up Advanced Stats</h4>
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Batting Average:</strong> {{ stats.batting_average }}</p>
                    <p><strong>Strike Rate:</strong> {{ stats.strike_rate }}%</p>
                    <p><strong>Best Batting Score:</strong> {{ stats.best_batting_score }}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Bowling Economy:</strong> {{ stats.bowling_economy }}</p>
                    <p><strong>Best Bowling Figures:</strong> {{ stats.best_bowling_figures }}</p>
                    <p><strong>Fielding Catches:</strong> {{ stats.fielding_catches }}</p>
                </div>
            </div>
            <p><strong>Recent Form:</strong> {{ stats.recent_form }}</p>
            <p><em>{{ stats.auction_notes }}</em></p>
            <hr>
            <div class="bid-section">
                <h5>Current Auction Price: ₹{{ player.price }}</h5>
                <button class="btn btn-light" onclick="window.location.href='{{ url_for('auction') }}#price_{{ name }}'">Go Back & Bid</button>
            </div>
        </div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
