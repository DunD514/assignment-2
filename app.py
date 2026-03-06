from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import pandas as pd

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Load players from Excel
df = pd.read_excel("players.xlsx")

players = {}

for _, row in df.iterrows():
    players[row["name"]] = {
        "price": int(row["base_price"]),
        "runs": row["runs"],
        "wickets": row["wickets"],
        "matches": row["matches"],
        "role": row["role"]
    }

html = """
<!DOCTYPE html>
<html>
<head>
<title>IPL Auction</title>
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>

<body>

<h1>IPL Auction</h1>

<table border="1">
<tr>
<th>Player</th>
<th>Role</th>
<th>Runs</th>
<th>Wickets</th>
<th>Price</th>
<th>Bid</th>
</tr>

{% for p in players %}
<tr>
<td>{{p}}</td>
<td>{{players[p]["role"]}}</td>
<td>{{players[p]["runs"]}}</td>
<td>{{players[p]["wickets"]}}</td>
<td id="{{p}}">{{players[p]["price"]}}</td>
<td><button onclick="bid('{{p}}')">Bid</button></td>
</tr>
{% endfor %}

</table>

<script>

var socket = io();

function bid(player){

let price = prompt("Enter bid");

socket.emit("place_bid",{
player:player,
bid:price
});

}

socket.on("price_update",function(data){
document.getElementById(data.player).innerText = data.price;
});

socket.on("error",function(data){
alert(data.msg);
});

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(html, players=players)

@socketio.on("place_bid")
def handle_bid(data):

    player = data["player"]
    bid = int(data["bid"])

    if bid > players[player]["price"]:

        players[player]["price"] = bid

        emit("price_update",{
            "player":player,
            "price":bid
        },broadcast=True)

    else:
        emit("error",{"msg":"Bid must be higher than current price"})

if __name__ == "__main__":
    socketio.run(app,host="0.0.0.0",port=10000)