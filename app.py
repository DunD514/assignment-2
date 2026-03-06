from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import pandas as pd
import psycopg2
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Connect to Render PostgreSQL
DATABASE_URL ='postgresql://ipl_auction_db_cusl_user:cGeaQvFN6VJj2h5mS2TNPyR6XxVXEOQG@dpg-d6l7i2s50q8c73bo4b6g-a/ipl_auction_db_cusl'

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Create table if not exists
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

# Import players from Excel if DB empty
cur.execute("SELECT COUNT(*) FROM players")
count = cur.fetchone()[0]

if count == 0:
    df = pd.read_excel("players.xlsx")

    for _, row in df.iterrows():
        cur.execute("""
        INSERT INTO players(name,price,runs,wickets,matches,role)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,
        (
            row["name"],
            row["base_price"],
            row["runs"],
            row["wickets"],
            row["matches"],
            row["role"]
        ))

    conn.commit()


# Load players from DB
def get_players():

    cur.execute("SELECT name,price,runs,wickets,matches,role FROM players")
    rows = cur.fetchall()

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


html = """

<!DOCTYPE html>
<html>

<head>

<title>IPL Live Auction</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

<style>

body{
background:#0f172a;
color:white;
}

.card{
background:#1e293b;
border:none;
}

.player-row:hover{
background:#334155;
}

.price{
font-weight:bold;
color:#22c55e;
font-size:18px;
}

</style>

</head>


<body>

<div class="container mt-4">

<h1 class="text-center mb-4">🏏 IPL Live Auction</h1>


<div class="row mb-3">

<div class="col-md-4">
<input class="form-control" id="search" placeholder="Search Player">
</div>

<div class="col-md-4">
<select class="form-select" id="roleFilter">
<option value="all">All Roles</option>
<option>Batsman</option>
<option>Bowler</option>
<option>All-rounder</option>
<option>Wicketkeeper</option>
</select>
</div>

</div>


<div class="card p-3">

<table class="table table-dark table-hover">

<thead>

<tr>
<th>Player</th>
<th>Role</th>
<th>Runs</th>
<th>Wickets</th>
<th>Matches</th>
<th>Current Price</th>
<th>Status</th>
<th>Bid</th>
</tr>

</thead>

<tbody id="playerTable">

{% for p in players %}

<tr class="player-row" data-role="{{players[p]['role']}}">

<td>{{p}}</td>
<td>{{players[p]["role"]}}</td>
<td>{{players[p]["runs"]}}</td>
<td>{{players[p]["wickets"]}}</td>
<td>{{players[p]["matches"]}}</td>

<td class="price" id="{{p}}">{{players[p]["price"]}}</td>

<td id="status_{{p}}">Waiting</td>

<td>

<button class="btn btn-success btn-sm" onclick="bid('{{p}}')">
Bid
</button>

</td>

</tr>

{% endfor %}

</tbody>

</table>

</div>

</div>


<script>

var socket = io({
    transports:["websocket","polling"]
});


function bid(player){

let price = prompt("Enter your bid");

if(price){

socket.emit("place_bid",{
player:player,
bid:price
});

}

}


socket.on("price_update",function(data){

let priceCell = document.getElementById(data.player);
let statusCell = document.getElementById("status_"+data.player);

priceCell.innerText = data.price;

priceCell.style.transform = "scale(1.3)";

setTimeout(()=>{
priceCell.style.transform="scale(1)";
},300);

statusCell.innerHTML = "🔥 New Bid";

setTimeout(()=>{
statusCell.innerHTML = "Waiting";
},2000);

});


socket.on("error",function(data){
alert(data.msg);
});


// SEARCH

document.getElementById("search").addEventListener("keyup",function(){

let filter = this.value.toLowerCase();

let rows = document.querySelectorAll("#playerTable tr");

rows.forEach(function(row){

let name = row.children[0].innerText.toLowerCase();

row.style.display = name.includes(filter) ? "" : "none";

});

});


// ROLE FILTER

document.getElementById("roleFilter").addEventListener("change",function(){

let role = this.value;

let rows = document.querySelectorAll("#playerTable tr");

rows.forEach(function(row){

let r = row.getAttribute("data-role");

if(role=="all" || r==role){

row.style.display="";

}else{

row.style.display="none";

}

});

});

</script>


</body>
</html>

"""


@app.route("/")
def home():
    players = get_players()
    return render_template_string(html, players=players)


@socketio.on("place_bid")
def handle_bid(data):

    player = data["player"]
    bid = int(data["bid"])

    cur.execute("SELECT price FROM players WHERE name=%s", (player,))
    current = cur.fetchone()[0]

    if bid > current:

        cur.execute(
        "UPDATE players SET price=%s WHERE name=%s",
        (bid,player)
        )

        conn.commit()

        emit("price_update",{
            "player":player,
            "price":bid
        },broadcast=True)

    else:

        emit("error",{"msg":"Bid must be higher than current price"})


if __name__ == "__main__":
    socketio.run(app,host="0.0.0.0",port=10000)
