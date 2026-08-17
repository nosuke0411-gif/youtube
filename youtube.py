from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "secret_key_here"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        coins INTEGER DEFAULT 100
    )
    """)
    conn.commit()
    conn.close()


init_db()


class User(UserMixin):
    def __init__(self, id, username, password_hash, coins):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.coins = coins


def get_user_by_username(username):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, coins FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1], row[2], row[3])
    return None


def get_user_by_id(user_id):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, coins FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1], row[2], row[3])
    return None


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)
def convert_youtube_url(url: str) -> str:
    base_mobile = "https://m.youtube.com/watch?v="
    base_pc = "https://www.youtube.com/watch?v="
    base_short = "https://youtu.be/"

    if url.startswith(base_short):
        return url
    if url.startswith(base_mobile):
        video_id = url[len(base_mobile):]
        return f"https://youtu.be/{video_id}"
    if url.startswith(base_pc):
        video_id = url[len(base_pc):]
        return f"https://youtu.be/{video_id}"

    raise ValueError("対応していないURL形式です")


@app.route("/")
def index():
    logged_in = current_user.is_authenticated
    login_button = """
    <button id="loginBtn" onclick="location.href='/login'">ログイン</button>
    """ if not logged_in else """
    <button id="loginBtn" onclick="location.href='/games'">ゲームへ</button>
    """

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>YouTube URL 変換ツール</title>
<style>
    body {{
        font-family: sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
        background: #f7f7f7;
    }}
    .top-bar {{
        position: fixed;
        top: 10px;
        right: 10px;
    }}
    #loginBtn {{
        padding: 8px 14px;
        font-size: 14px;
        border-radius: 6px;
        border: none;
        background: #28a745;
        color: white;
        cursor: pointer;
    }}
    .container {{
        text-align: center;
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 0 15px rgba(0,0,0,0.1);
        width: 90%;
        max-width: 500px;
    }}
    .input-area {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    input {{
        flex: 9;
        padding: 14px;
        font-size: 18px;
        border-radius: 8px;
        border: 1px solid #ccc;
    }}
    #clearInputBtn {{
        flex: 1;
        padding: 6px;
        font-size: 14px;
        background: #dc3545;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
    }}
    #convertBtn {{
        padding: 14px;
        font-size: 18px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        width: 100%;
        margin-top: 15px;
    }}
    #openBtn {{
        padding: 14px;
        font-size: 18px;
        background: #28a745;
        color: white;
        border: none;
        border-radius: 8px;
        width: 100%;
        margin-top: 15px;
        display: none;
    }}
    #status {{
        margin-top: 20px;
        font-size: 18px;
        font-weight: bold;
    }}
</style>
</head>
<body>

<div class="top-bar">
    {login_button}
</div>

<div class="container">
    <h1>YouTube URL 変換ツール</h1>

    <div class="input-area">
        <input id="urlInput" type="text" placeholder="URLを入力">
        <button id="clearInputBtn" onclick="clearInput()">✖️</button>
    </div>

    <button id="convertBtn" onclick="convert()">変換する</button>
    <button id="openBtn" onclick="openUrl()">開く</button>

    <p id="status"></p>
</div>

<script>
    async function convert() {{
        const url = document.getElementById("urlInput").value;

        const res = await fetch("/convert", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{url}})
        }});

        const data = await res.json();

        if (data.success) {{
            window.convertedUrl = data.converted;
            document.getElementById("status").innerText = "Connection successful";
            document.getElementById("openBtn").style.display = "block";
        }} else {{
            document.getElementById("status").innerText = "Error: " + data.error;
            document.getElementById("openBtn").style.display = "none";
        }}
    }}

    function openUrl() {{
        if (window.convertedUrl) {{
            window.open(window.convertedUrl, "_blank");
        }}
    }}

    function clearInput() {{
        document.getElementById("urlInput").value = "";
        document.getElementById("status").innerText = "";
        document.getElementById("openBtn").style.display = "none";
        window.convertedUrl = null;
    }}
</script>

</body>
</html>
"""
@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    url = data.get("url")

    try:
        result = convert_youtube_url(url)
        return jsonify({"success": True, "converted": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
@app.route("/games")
@login_required
def games():
    return render_template_string(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Games</title>
<style>
    body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center;
           height: 100vh; margin: 0; background: #f7f7f7; }}
    .container {{ text-align: center; background: white; padding: 40px; border-radius: 12px;
                 box-shadow: 0 0 15px rgba(0,0,0,0.1); width: 90%; max-width: 400px; }}
    button {{ width: 100%; padding: 14px; margin-top: 10px; font-size: 18px; border: none;
             border-radius: 8px; background: #007bff; color: white; cursor: pointer; }}
    a {{ display: block; margin-top: 15px; color: #007bff; text-decoration: none; }}
</style>
</head>
<body>

<div class="container">
    <h2>ゲーム一覧</h2>
    <p>ようこそ、{current_user.username} さん</p>
    <button onclick="location.href='/slot'">3×3 スロット</button>
    <button onclick="location.href='/highlow'">ハイロー</button>
    <a href="/">変換ツールに戻る</a>
    <a href="/logout">ログアウト</a>
</div>

</body>
</html>
""")


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")
@app.route("/slot_spin", methods=["POST"])
@login_required
def slot_spin():
    data = request.json
    bet = int(data.get("bet", 10))

    symbols = ["🍒", "🍋", "⭐", "💎", "7️⃣"]
    grid = [[random.choice(symbols) for _ in range(3)] for _ in range(3)]

    lines = [
        grid[0],
        grid[1],
        grid[2],
        [grid[0][0], grid[1][0], grid[2][0]],
        [grid[0][1], grid[1][1], grid[2][1]],
        [grid[0][2], grid[1][2], grid[2][2]],
        [grid[0][0], grid[1][1], grid[2][2]],
        [grid[0][2], grid[1][1], grid[0][0]],
    ]

    total_multiplier = 0

    for line in lines:
        if line[0] == line[1] == line[2]:
            total_multiplier += 5

    win = bet * total_multiplier

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=?", (current_user.id,))
    coins = cur.fetchone()[0]

    coins = coins - bet + win

    cur.execute("UPDATE users SET coins=? WHERE id=?", (coins, current_user.id))
    conn.commit()
    conn.close()

    return jsonify({
        "grid": grid,
        "win": win,
        "multiplier": total_multiplier,
        "coins": coins
    })
@app.route("/get_coins")
@login_required
def get_coins():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=?", (current_user.id,))
    coins = cur.fetchone()[0]
    conn.close()
    return jsonify({"coins": coins})
@app.route("/slot")
@login_required
def slot():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Slot 3x3</title>
<style>
    body { font-family: sans-serif; text-align: center; background: #f7f7f7; }

    .grid {
        display: grid;
        grid-template-columns: repeat(3, 80px);
        gap: 10px;
        justify-content: center;
        margin-top: 30px;
    }

    .cell {
        font-size: 50px;
        width: 80px;
        height: 80px;
        background: white;
        border-radius: 10px;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow: 0 0 10px rgba(0,0,0,0.2);
        transition: box-shadow 0.3s, transform 0.3s;
    }

    .spin {
        animation: spinAnim 0.1s infinite;
    }

    @keyframes spinAnim {
        0% { transform: rotate(0deg); }
        50% { transform: rotate(10deg); }
        100% { transform: rotate(0deg); }
    }

    .win {
        box-shadow: 0 0 20px gold;
    }

    button {
        padding: 14px;
        font-size: 20px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        margin-top: 20px;
    }
</style>
</head>
<body>

<h2>3×3 スロット</h2>
<p>コイン: <span id="coins">読み込み中...</span></p>

<p>
    ベット額:
    <input id="bet" type="number" value="10" min="1" style="width:80px; font-size:18px;">
</p>

<div class="grid">
    <div class="cell" id="c0"></div>
    <div class="cell" id="c1"></div>
    <div class="cell" id="c2"></div>
    <div class="cell" id="c3"></div>
    <div class="cell" id="c4"></div>
    <div class="cell" id="c5"></div>
    <div class="cell" id="c6"></div>
    <div class="cell" id="c7"></div>
    <div class="cell" id="c8"></div>
</div>

<button onclick="spin()">回す</button>
<button onclick="location.href='/games'" style="margin-top:20px;">ゲーム一覧に戻る</button>

<p id="result"></p>

<script>
function animateAll() {
    for (let i = 0; i < 9; i++) {
        document.getElementById("c" + i).classList.add("spin");
    }
}

function stopAnimation() {
    for (let i = 0; i < 9; i++) {
        document.getElementById("c" + i).classList.remove("spin");
    }
}

async function spin() {
    document.getElementById("result").innerText = "";
    animateAll();

    const bet = Number(document.getElementById("bet").value);

    const res = await fetch("/slot_spin", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ bet })
    });

    const data = await res.json();

    setTimeout(() => {
        stopAnimation();

        let flat = [].concat(...data.grid);

        for (let i = 0; i < 9; i++) {
            document.getElementById("c" + i).innerText = flat[i];
            document.getElementById("c" + i).classList.remove("win");
        }

        if (data.multiplier > 0) {
            highlightWins(data.grid);
        }

        document.getElementById("coins").innerText = data.coins;

        if (data.multiplier === 0) {
            document.getElementById("result").innerText = "😢 ハズレ…";
        } else {
            document.getElementById("result").innerText =
                "🎉 当たり！ +" + data.win + "（倍率 " + data.multiplier + "）";
        }

    }, 1000);
}

function highlightWins(grid) {
    const lines = [
        [0,1,2], [3,4,5], [6,7,8],
        [0,3,6], [1,4,7], [2,5,8],
        [0,4,8], [2,4,6]
    ];

    for (let line of lines) {
        const a = grid[Math.floor(line[0]/3)][line[0]%3];
        const b = grid[Math.floor(line[1]/3)][line[1]%3];
        const c = grid[Math.floor(line[2]/3)][line[2]%3];

        if (a === b && b === c) {
            line.forEach(i => document.getElementById("c" + i).classList.add("win"));
        }
    }
}

fetch("/get_coins").then(r => r.json()).then(d => {
    document.getElementById("coins").innerText = d.coins;
});
</script>

</body>
</html>
"""
def generate_card():
    value = random.randint(1, 13)
    suit = random.choice(["♠️", "♥️", "♦️", "♣️"])
    return value, suit


def calc_multiplier(current_value, choice):
    if choice == "high":
        prob = (13 - current_value) / 13
    else:
        prob = (current_value - 1) / 13

    if prob <= 0:
        return None

    return round(1 / prob, 3)


@app.route("/highlow")
@login_required
def highlow():
    value, suit = generate_card()

    return render_template_string(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>High & Low</title>
<style>
    body {{
        font-family: sans-serif;
        text-align: center;
        background: #f7f7f7;
    }}
    .card {{
        font-size: 60px;
        background: white;
        padding: 30px;
        border-radius: 12px;
        display: inline-block;
        margin-top: 30px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2);
    }}
    button {{
        padding: 14px;
        font-size: 20px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        margin-top: 20px;
        width: 200px;
    }}
</style>
</head>
<body>

<h2>High & Low</h2>
<p>コイン: <span id="coins">{current_user.coins}</span></p>

<p>現在のカード</p>
<div class="card">{suit} {value}</div>

<p>
    ベット額:
    <input id="bet" type="number" value="10" min="1" style="width:80px; font-size:18px;">
</p>

<button onclick="play('high', {value})">High</button><br>
<button onclick="play('low', {value})">Low</button><br>
<button onclick="location.href='/games'" style="margin-top:20px;">ゲーム一覧に戻る</button>

<p id="result"></p>

<script>
async function play(choice, current_value) {{
    const bet = Number(document.getElementById("bet").value);

    const res = await fetch("/highlow_play", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
            choice: choice,
            current_value: current_value,
            bet: bet
        }})
    }});

    const data = await res.json();

    document.body.innerHTML = data.html;
}}
</script>

</body>
</html>
""")
@app.route("/highlow_play", methods=["POST"])
@login_required
def highlow_play():
    data = request.json
    choice = data["choice"]
    current_value = int(data["current_value"])
    bet = int(data["bet"])

    next_value, next_suit = generate_card()

    if next_value == current_value:
        html = f"""
        <h2>引き分け！</h2>
        <p>次のカードへ進みます</p>
        <div class='card'>{next_suit} {next_value}</div>
        <button onclick="location.href='/highlow_continue?value={next_value}&suit={next_suit}&bet={bet}'">続ける</button>
        <button onclick="location.href='/games'">ゲーム一覧へ</button>
        """
        return jsonify({"html": html})

    if choice == "high":
        win = next_value > current_value
    else:
        win = next_value < current_value

    multiplier = calc_multiplier(current_value, choice)

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=?", (current_user.id,))
    coins = cur.fetchone()[0]

    if win:
        gain = int(bet * multiplier)
        coins += gain
        result_text = f"勝ち！ +{gain}（倍率 {multiplier}）"
    else:
        coins -= bet
        result_text = f"負け… -{bet}"

    cur.execute("UPDATE users SET coins=? WHERE id=?", (coins, current_user.id))
    conn.commit()
    conn.close()

    html = f"""
    <h2>{result_text}</h2>
    <p>次のカード</p>
    <div class='card'>{next_suit} {next_value}</div>
    <button onclick="location.href='/highlow_continue?value={next_value}&suit={next_suit}&bet={bet}'">続ける</button>
    <button onclick="location.href='/games'">ゲーム一覧へ</button>
    """

    return jsonify({"html": html})
@app.route("/highlow_continue")
@login_required
def highlow_continue():
    value = int(request.args.get("value"))
    suit = request.args.get("suit")
    bet = int(request.args.get("bet"))

    return render_template_string(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>High & Low</title>
<style>
    body {{
        font-family: sans-serif;
        text-align: center;
        background: #f7f7f7;
    }}
    .card {{
        font-size: 60px;
        background: white;
        padding: 30px;
        border-radius: 12px;
        display: inline-block;
        margin-top: 30px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2);
    }}
    button {{
        padding: 14px;
        font-size: 20px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        margin-top: 20px;
        width: 200px;
    }}
</style>
</head>
<body>

<h2>High & Low（続き）</h2>
<p>コイン: {current_user.coins}</p>

<p>現在のカード</p>
<div class="card">{suit} {value}</div>

<p>
    ベット額:
    <input id="bet" type="number" value="{bet}" min="1" style="width:80px; font-size:18px;">
</p>

<button onclick="play('high', {value})">High</button><br>
<button onclick="play('low', {value})">Low</button><br>
<button onclick="location.href='/games'" style="margin-top:20px;">ゲーム一覧に戻る</button>

<p id="result"></p>

<script>
async function play(choice, current_value) {{
    const bet = Number(document.getElementById("bet").value);

    const res = await fetch("/highlow_play", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
            choice: choice,
            current_value: current_value,
            bet: bet
        }})
    }});

    const data = await res.json();
    document.body.innerHTML = data.html;
}}
</script>

</body>
</html>
""")
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)
