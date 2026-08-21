from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import random
import psycopg2
import itertools
from collections import Counter
from supabase import create_client
import os
from supabase import create_client

app = Flask(__name__)
app.secret_key = "secret_key_here"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ==========================
# DB 接続（Supabase / PostgreSQL）
# ==========================
def get_conn():
    return psycopg2.connect(
        host="aws-0-ap-northeast-1.pooler.supabase.com",
        database="postgres",
        user="postgres.txfrrpxosbhytshmwzkq",
        password="nosuke0411!",
        port=5432
    )

# ==========================
# User クラス
# ==========================
class User(UserMixin):
    def __init__(self, id, username, password_hash, coins):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.coins = coins

def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, coins FROM users WHERE username=%s", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1], row[2], row[3])
    return None

def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, coins FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1], row[2], row[3])
    return None

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

# ==========================
# YouTube URL 変換ロジック
# ==========================
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

# ==========================
# トップページ
# ==========================
@app.route("/")
def index():
    logged_in = current_user.is_authenticated
    login_button = (
        '<button id="loginBtn" onclick="location.href=\'/login\'">ログイン</button>'
        if not logged_in else
        '<button id="loginBtn" onclick="location.href=\'/games\'">ゲームへ</button>'
    )

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>YouTube URL 変換ツール</title>
<style>
    body {
        font-family: sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
        background: #f7f7f7;
    }
    .top-bar {
        position: fixed;
        top: 10px;
        right: 10px;
    }
    #loginBtn {
        padding: 8px 14px;
        font-size: 14px;
        border-radius: 6px;
        border: none;
        background: #28a745;
        color: white;
        cursor: pointer;
    }
    .container {
        text-align: center;
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 0 15px rgba(0,0,0,0.1);
        width: 90%;
        max-width: 500px;
    }
    .input-area {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    input {
        flex: 9;
        padding: 14px;
        font-size: 18px;
        border-radius: 8px;
        border: 1px solid #ccc;
    }
    #clearInputBtn {
        flex: 1;
        padding: 6px;
        font-size: 14px;
        background: #dc3545;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
    }
    #convertBtn {
        padding: 14px;
        font-size: 18px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        width: 100%;
        margin-top: 15px;
    }
    #openBtn {
        padding: 14px;
        font-size: 18px;
        background: #28a745;
        color: white;
        border: none;
        border-radius: 8px;
        width: 100%;
        margin-top: 15px;
        display: none;
    }
    #status {
        margin-top: 20px;
        font-size: 18px;
        font-weight: bold;
    }
</style>
</head>
<body>

<div class="top-bar">
    {{ login_button|safe }}
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
    async function convert() {
        const url = document.getElementById("urlInput").value;

        const res = await fetch("/convert", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({url})
        });

        const data = await res.json();

        if (data.success) {
            window.convertedUrl = data.converted;
            document.getElementById("status").innerText = "変換成功";
            document.getElementById("openBtn").style.display = "block";
        } else {
            document.getElementById("status").innerText = "エラー: " + data.error;
            document.getElementById("openBtn").style.display = "none";
        }
    }

    function openUrl() {
        if (window.convertedUrl) {
            window.open(window.convertedUrl, "_blank");
        }
    }

    function clearInput() {
        document.getElementById("urlInput").value = "";
        document.getElementById("status").innerText = "";
        document.getElementById("openBtn").style.display = "none";
        window.convertedUrl = null;
    }
</script>

</body>
</html>
""", login_button=login_button)

# ==========================
# /convert API
# ==========================
@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    url = data.get("url")

    try:
        result = convert_youtube_url(url)
        return jsonify({"success": True, "converted": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
# ==========================
# ログイン
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = get_user_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("games"))

        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Login Failed</title>
<style>
    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center;
           height: 100vh; margin: 0; background: #f7f7f7; }
    .container { text-align: center; background: white; padding: 40px; border-radius: 12px;
                 box-shadow: 0 0 15px rgba(0,0,0,0.1); width: 90%; max-width: 400px; }
    a { display: block; margin-top: 15px; color: #007bff; text-decoration: none; font-size: 18px; }
</style>
</head>
<body>

<div class="container">
    <h2>ログイン失敗しました</h2>
    <p>ユーザー名またはパスワードが違います。</p>

    <a href="/login">ログイン画面に戻る</a>
    <a href="/">変換ツールに戻る</a>
</div>

</body>
</html>
""")

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Login</title>
<style>
    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center;
           height: 100vh; margin: 0; background: #f7f7f7; }
    .container { text-align: center; background: white; padding: 40px; border-radius: 12px;
                 box-shadow: 0 0 15px rgba(0,0,0,0.1); width: 90%; max-width: 400px; }
    input { width: 100%; padding: 14px; margin-top: 10px; font-size: 18px; border-radius: 8px;
            border: 1px solid #ccc; }
    button { width: 100%; padding: 14px; margin-top: 20px; font-size: 18px; border: none;
             border-radius: 8px; background: #007bff; color: white; cursor: pointer; }
    a { display: block; margin-top: 15px; color: #007bff; text-decoration: none; }
</style>
</head>
<body>

<div class="container">
    <h2>ログイン</h2>

    <form method="POST">
        <input type="text" name="username" placeholder="ユーザー名">
        <input type="password" name="password" placeholder="パスワード">
        <button type="submit">ログイン</button>
    </form>

    <a href="/register">新規登録はこちら</a>
    <a href="/">変換ツールに戻る</a>
</div>

</body>
</html>
""")

# ==========================
# 新規登録
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, generate_password_hash(password))
            )
            conn.commit()

        except psycopg2.errors.UniqueViolation:
            conn.close()
            return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Register Failed</title>
<style>
    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center;
           height: 100vh; margin: 0; background: #f7f7f7; }
    .container { text-align: center; background: white; padding: 40px; border-radius: 12px;
                 box-shadow: 0 0 15px rgba(0,0,0,0.1); width: 90%; max-width: 400px; }
    a { display: block; margin-top: 15px; color: #007bff; text-decoration: none; font-size: 18px; }
</style>
</head>
<body>

<div class="container">
    <h2>新規登録に失敗しました</h2>
    <p>そのユーザー名は既に使われています。</p>

    <a href="/register">新規登録画面に戻る</a>
    <a href="/">変換ツールに戻る</a>
</div>

</body>
</html>
""")

        conn.close()
        return redirect("/login")

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Register</title>
<style>
    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center;
           height: 100vh; margin: 0; background: #f7f7f7; }
    .container { text-align: center; background: white; padding: 40px; border-radius: 12px;
                 box-shadow: 0 0 15px rgba(0,0,0,0.1); width: 90%; max-width: 400px; }
    input { width: 100%; padding: 14px; margin-top: 10px; font-size: 18px; border-radius: 8px;
            border: 1px solid #ccc; }
    button { width: 100%; padding: 14px; margin-top: 20px; font-size: 18px; border: none;
             border-radius: 8px; background: #28a745; color: white; cursor: pointer; }
    a { display: block; margin-top: 15px; color: #007bff; text-decoration: none; }
</style>
</head>
<body>

<div class="container">
    <h2>新規登録</h2>

    <form method="POST">
        <input type="text" name="username" placeholder="ユーザー名">
        <input type="password" name="password" placeholder="パスワード">
        <button type="submit">登録する</button>
    </form>

    <a href="/login">ログイン画面へ</a>
</div>

</body>
</html>
""")

# ==========================
# ゲーム一覧
# ==========================
@app.route("/games")
@login_required
def games():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Games</title>
<style>
    body { font-family: sans-serif; text-align: center; background: #f7f7f7; padding-top: 60px; }
    .container {
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 0 15px rgba(0,0,0,0.1);
        width: 90%;
        max-width: 400px;
        margin: auto;
    }
    button {
        width: 100%;
        padding: 14px;
        margin-top: 10px;
        font-size: 18px;
        border: none;
        border-radius: 8px;
        background: #007bff;
        color: white;
        cursor: pointer;
    }
    a {
        display: block;
        margin-top: 15px;
        color: #007bff;
        text-decoration: none;
    }
</style>
</head>
<body>

<div class="container">
    <h2>ゲーム一覧</h2>
    <p>ようこそ、{{ username }} さん</p>

    <button onclick="location.href='/slot'">3×3 スロット</button>
    <button onclick="location.href='/highlow'">ハイロー</button>
    <button onclick="location.href='/mines'">マイン</button>
    <button onclick="location.href='/poker'">ポーカー（ボット戦）</button>
    <button onclick="location.href='/holdem_room'">テキサスホールデム（対人戦）</button>

    <a href="/">変換ツールに戻る</a>
    <a href="/logout">ログアウト</a>
</div>

</body>
</html>
""", username=current_user.username)
# ==========================
# コイン取得API
# ==========================
@app.route("/get_coins")
@login_required
def get_coins():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    row = cur.fetchone()
    conn.close()
    return jsonify({"coins": row[0]})

# ==========================
# スロット（UI）
# ==========================
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

    #backBtn {
        background: #28a745;
        margin-top: 10px;
    }
</style>
</head>
<body>

<h2>3×3 スロット</h2>
<p>コイン: <span id="coins">読み込み中...</span></p>

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

<p>
    ベット額:
    <input id="bet" type="number" value="10" min="1" style="width:80px; font-size:18px;">
</p>

<button onclick="spin()">回す</button>
<button id="backBtn" onclick="location.href='/games'">ゲーム一覧へ戻る</button>

<p id="result"></p>

<script>
const symbols = ["🍒", "🍋", "⭐", "💎", "7️⃣"];

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
""")

# ==========================
# スロット（結果処理）
# ==========================
@app.route("/slot_spin", methods=["POST"])
@login_required
def slot_spin():
    data = request.json
    bet = int(data.get("bet", 10))

    if bet <= 0:
        return jsonify({
            "error": True,
            "html": """
            <div style='text-align:center; padding:40px; background:white; border-radius:12px; width:90%; max-width:400px; margin:40px auto; box-shadow:0 0 15px rgba(0,0,0,0.1);'>
                <h2>エラー</h2>
                <p>ベット額が不正です（0以下は不可）</p>
                <button onclick="location.href='/games'" style='padding:14px; font-size:18px; background:#28a745; color:white; border:none; border-radius:8px; cursor:pointer; width:200px; margin-top:20px;'>ゲーム一覧へ戻る</button>
            </div>
            """
        }), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    if bet > coins:
        conn.close()
        return jsonify({
            "error": True,
            "html": f"""
            <div style='text-align:center; padding:40px; background:white; border-radius:12px; width:90%; max-width:400px; margin:40px auto; box-shadow:0 0 15px rgba(0,0,0,0.1);'>
                <h2>エラー</h2>
                <p>持ち金が足りません（現在 {coins} コイン）</p>
                <button onclick="location.href='/games'" style='padding:14px; font-size:18px; background:#28a745; color:white; border:none; border-radius:8px; cursor:pointer; width:200px; margin-top:20px;'>ゲーム一覧へ戻る</button>
            </div>
            """
        }), 400

    symbols = ["🍒", "🍋", "⭐", "💎", "7️⃣"]
    grid = [[random.choice(symbols) for _ in range(3)] for _ in range(3)]

    lines = [
        grid[0], grid[1], grid[2],
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
    coins = coins - bet + win
    if coins < 0:
        coins = 0

    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()
    conn.close()

    return jsonify({
        "grid": grid,
        "win": win,
        "multiplier": total_multiplier,
        "coins": coins,
        "error": False
    })
# ==========================
# ハイロー（カード生成・倍率計算）
# ==========================
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

# ==========================
# ハイロー（初期画面）
# ==========================
@app.route("/highlow")
@login_required
def highlow():
    value, suit = generate_card()
    coins = current_user.coins

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>High & Low</title>
<style>
    body {
        font-family:sans-serif;
        background:#f7f7f7;
        text-align:center;
        padding-top:40px;
    }
    .card {
        font-size:50px;
        background:white;
        padding:25px 40px;
        border-radius:12px;
        display:inline-block;
        margin:10px;
        box-shadow:0 0 15px rgba(0,0,0,0.2);
    }
    .row {
        display:flex;
        justify-content:center;
        align-items:center;
        gap:40px;
        margin-top:30px;
    }
    button {
        padding:14px;
        font-size:20px;
        background:#007bff;
        color:white;
        border:none;
        border-radius:8px;
        cursor:pointer;
        margin-top:20px;
        width:200px;
    }
    #backBtn {
        background:#28a745;
        margin-top:10px;
    }
</style>
</head>
<body>

<h2>High & Low</h2>
<p>コイン: {{ coins }}</p>

<div id="game">

    <div class="row">
        <div class="card">{{ suit }} {{ value }}</div>
        <div class="card">？</div>
    </div>

    <p>
        ベット額:
        <input id="bet" type="number" value="10" min="1" style="width:80px; font-size:18px;">
    </p>

    <button onclick="startGame({{ value }}, '{{ suit }}')">ゲーム開始</button><br>
    <button id="backBtn" onclick="location.href='/games'">ゲーム一覧へ戻る</button>

</div>

<script>
async function startGame(current_value, current_suit) {
    const bet = Number(document.getElementById("bet").value);

    const res = await fetch("/highlow_start", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            current_value,
            current_suit,
            bet
        })
    });

    const data = await res.json();
    document.getElementById("game").innerHTML = data.html;
}

async function play(choice, current_value, current_suit, bet, multiplier) {
    const res = await fetch("/highlow_play2", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            choice,
            current_value,
            current_suit,
            bet,
            multiplier
        })
    });

    const data = await res.json();
    document.getElementById("game").innerHTML = data.html;
}
</script>

</body>
</html>
""", coins=coins, value=value, suit=suit)

# ==========================
# ハイロー（初回ベットを引く）
# ==========================
@app.route("/highlow_start", methods=["POST"])
@login_required
def highlow_start():
    data = request.json
    current_value = int(data["current_value"])
    current_suit = data["current_suit"]
    bet = int(data["bet"])

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    if bet <= 0:
        conn.close()
        return jsonify({
            "html": """
            <div style='text-align:center; padding:40px; background:white; border-radius:12px;
                        width:90%; max-width:400px; margin:40px auto;
                        box-shadow:0 0 15px rgba(0,0,0,0.1);'>
                <h2>エラー</h2>
                <p>ベット額が不正です（0以下は不可）</p>
                <button onclick="location.href='/games'" 
                        style='padding:14px; font-size:18px; background:#28a745; color:white;
                               border:none; border-radius:8px; cursor:pointer; width:200px;
                               margin-top:20px;'>ゲーム一覧へ戻る</button>
            </div>
            """
        }), 400

    if bet > coins:
        conn.close()
        return jsonify({
            "html": f"""
            <div style='text-align:center; padding:40px; background:white; border-radius:12px;
                        width:90%; max-width:400px; margin:40px auto;
                        box-shadow:0 0 15px rgba(0,0,0,0.1);'>
                <h2>エラー</h2>
                <p>持ち金が足りません（現在 {coins} コイン）</p>
                <button onclick="location.href='/games'" 
                        style='padding:14px; font-size:18px; background:#28a745; color:white;
                               border:none; border-radius:8px; cursor:pointer; width:200px;
                               margin-top:20px;'>ゲーム一覧へ戻る</button>
            </div>
            """
        }), 400

    coins -= bet
    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()
    conn.close()

    multiplier = 1.0

    html = f"""
    <p>コイン: {coins}</p>

    <div class="row">
        <div class="card">{current_suit} {current_value}</div>
        <div class="card">？</div>
    </div>

    <p>累積倍率: {multiplier}</p>

    <button onclick="play('high', {current_value}, '{current_suit}', {bet}, {multiplier})">High</button><br>
    <button onclick="play('low', {current_value}, '{current_suit}', {bet}, {multiplier})">Low</button><br>

    <button onclick="location.href='/games'">ゲーム一覧へ戻る</button>
    """

    return jsonify({"html": html})

# ==========================
# ハイロー（勝敗処理）
# ==========================
@app.route("/highlow_play2", methods=["POST"])
@login_required
def highlow_play2():
    data = request.json
    choice = data["choice"]
    current_value = int(data["current_value"])
    current_suit = data["current_suit"]
    bet = int(data["bet"])
    multiplier = float(data["multiplier"])

    next_value, next_suit = generate_card()

    if next_value == current_value:
        html = f"""
        <h2>引き分け！</h2>

        <div class="row">
            <div class="card">{current_suit} {current_value}</div>
            <div class="card">{next_suit} {next_value}</div>
        </div>

        <p>累積倍率: {multiplier}</p>

        <button onclick="play('high', {next_value}, '{next_suit}', {bet}, {multiplier})">High</button><br>
        <button onclick="play('low', {next_value}, '{next_suit}', {bet}, {multiplier})">Low</button><br>

        <button onclick="location.href='/highlow_cashout?bet={bet}&multiplier={multiplier}'">やめる（払い戻し）</button>
        <button onclick="location.href='/games'">ゲーム一覧へ</button>
        """
        return jsonify({"html": html})

    win = (next_value > current_value) if choice == "high" else (next_value < current_value)
    new_multiplier = calc_multiplier(current_value, choice)

    if win:
        multiplier *= new_multiplier
        result_text = f"勝ち！ 倍率 ×{new_multiplier} → 累積 {round(multiplier,3)}"
    else:
        multiplier = 0
        result_text = "負け…（払い戻しなし）"

    html = f"""
    <h2>{result_text}</h2>

    <div class="row">
        <div class="card">{current_suit} {current_value}</div>
        <div class="card">{next_suit} {next_value}</div>
    </div>

    <p>累積倍率: {round(multiplier,3)}</p>

    <button onclick="play('high', {next_value}, '{next_suit}', {bet}, {multiplier})">High</button><br>
    <button onclick="play('low', {next_value}, '{next_suit}', {bet}, {multiplier})">Low</button><br>

    <button onclick="location.href='/highlow_cashout?bet={bet}&multiplier={multiplier}'">やめる（払い戻し）</button>
    <button onclick="location.href='/games'">ゲーム一覧へ</button>
    """

    return jsonify({"html": html})

# ==========================
# ハイロー（やめる → 払い戻し）
# ==========================
@app.route("/highlow_cashout")
@login_required
def highlow_cashout():
    bet = float(request.args.get("bet"))
    multiplier = float(request.args.get("multiplier"))

    payout = int(bet * multiplier)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    coins += payout
    if coins < 0:
        coins = 0

    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()
    conn.close()

    return f"""
    <div style="
        background:white;
        padding:40px;
        border-radius:12px;
        box-shadow:0 0 15px rgba(0,0,0,0.1);
        width:90%;
        max-width:400px;
        margin:40px auto;
        text-align:center;
    ">
        <h2 style="margin-bottom:20px;">払い戻し</h2>
        <p style="font-size:24px; margin-bottom:10px;">+{payout} コイン</p>
        <p style="font-size:18px;">現在のコイン: {coins}</p>
    </div>

    <button onclick="location.href='/games'" style="
        padding:14px;
        font-size:20px;
        background:#28a745;
        color:white;
        border:none;
        border-radius:8px;
        cursor:pointer;
        width:200px;
        display:block;
        margin:20px auto;
    ">ゲーム一覧へ戻る</button>
    """
# ==========================
# ポーカー用ユーティリティ
# ==========================
SUITS = ["♠️", "♥️", "♦️", "♣️"]
VALUES = list(range(1, 14))

def generate_deck():
    deck = []
    for v in VALUES:
        for s in SUITS:
            deck.append((v, s))
    random.shuffle(deck)
    return deck

def evaluate_hand(hand):
    values = sorted([v for v, s in hand])
    suits = [s for v, s in hand]

    values_ace_high = [14 if v == 1 else v for v in values]
    values_ace_high_sorted = sorted(values_ace_high)

    from collections import Counter
    value_counts = Counter(values)
    suit_counts = Counter(suits)

    is_flush = (len(suit_counts) == 1)

    def is_straight(vals):
        return all(vals[i] + 1 == vals[i+1] for i in range(len(vals)-1))

    is_straight_low = is_straight(values)
    is_straight_high = is_straight(values_ace_high_sorted)
    is_straight_any = is_straight_low or is_straight_high

    counts = sorted(value_counts.values(), reverse=True)

    if counts == [4, 1]:
        rank = 8
        name = "フォーカード"
    elif counts == [3, 2]:
        rank = 7
        name = "フルハウス"
    elif is_flush and not is_straight_any:
        rank = 6
        name = "フラッシュ"
    elif is_straight_any and not is_flush:
        rank = 5
        name = "ストレート"
    elif counts == [3, 1, 1]:
        rank = 4
        name = "スリーカード"
    elif counts == [2, 2, 1]:
        rank = 3
        name = "ツーペア"
    elif counts == [2, 1, 1, 1]:
        rank = 2
        name = "ワンペア"
    else:
        rank = 1
        name = "ハイカード"

    if is_flush and is_straight_any:
        if set(values_ace_high_sorted) == {10, 11, 12, 13, 14}:
            rank = 10
            name = "ロイヤルストレートフラッシュ"
        else:
            rank = 9
            name = "ストレートフラッシュ"

    return rank, name

def bot_discard_indices(hand):
    from collections import Counter
    values = [v for v, s in hand]
    value_counts = Counter(values)

    rank, name = evaluate_hand(hand)
    discard = []

    if name == "ワンペア":
        pair_value = [v for v, c in value_counts.items() if c == 2][0]
        for i, (v, s) in enumerate(hand):
            if v != pair_value and len(discard) < 3:
                discard.append(i)

    elif name == "スリーカード":
        three_value = [v for v, c in value_counts.items() if c == 3][0]
        for i, (v, s) in enumerate(hand):
            if v != three_value:
                discard.append(i)

    elif name in ["ツーペア", "フルハウス", "フォーカード",
                  "ストレート", "フラッシュ",
                  "ストレートフラッシュ", "ロイヤルストレートフラッシュ"]:
        discard = []

    else:
        idxs = list(range(len(hand)))
        random.shuffle(idxs)
        discard = idxs[:2]

    return discard

# ==========================
# ポーカー（UI）
# ==========================
@app.route("/poker")
@login_required
def poker():
    coins = current_user.coins
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Poker (Bot)</title>
<style>
    body {
        font-family:sans-serif;
        background:#f7f7f7;
        text-align:center;
        padding-top:40px;
    }
    .card {
        font-size:32px;
        background:white;
        padding:15px 25px;
        border-radius:12px;
        display:inline-block;
        margin:10px;
        box-shadow:0 0 15px rgba(0,0,0,0.2);
    }
    .row {
        display:flex;
        justify-content:center;
        align-items:center;
        gap:10px;
        margin-top:20px;
        flex-wrap:wrap;
    }
    button {
        padding:14px;
        font-size:18px;
        background:#007bff;
        color:white;
        border:none;
        border-radius:8px;
        cursor:pointer;
        margin-top:20px;
        width:220px;
    }
    #backBtn {
        background:#28a745;
        margin-top:10px;
    }
</style>
</head>
<body>

<h2>Poker (5カードドロー・ボット戦)</h2>

<div id="startArea">

    <!-- ★ コイン表示をここに移動したので、開始後に消える ★ -->
    <p>コイン: {{ coins }}</p>

    <p>
        ベット額:
        <input id="bet" type="number" value="10" min="1" style="width:80px; font-size:18px;">
    </p>

    <button onclick="startPoker()">ボット戦を開始</button><br>
    <button id="backBtn" onclick="location.href='/games'">ゲーム一覧へ戻る</button>
</div>

<div id="game"></div>

<script>
async function startPoker() {
    const bet = Number(document.getElementById("bet").value);

    const res = await fetch("/poker_bot_start", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ bet })
    });

    const data = await res.json();

    // ★ startArea を消す → コイン表示も消える
    document.getElementById("startArea").innerHTML = "";
    document.getElementById("game").innerHTML = data.html;
}

async function drawPoker() {
    const checkboxes = document.querySelectorAll(".discard-checkbox");
    let discard = [];
    checkboxes.forEach((cb, idx) => {
        if (cb.checked) discard.push(idx);
    });

    const res = await fetch("/poker_bot_draw", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ discard })
    });

    const data = await res.json();
    document.getElementById("game").innerHTML = data.html;
}

async function resultPoker() {
    const res = await fetch("/poker_bot_result", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({})
    });

    const data = await res.json();
    document.getElementById("game").innerHTML = data.html;
}
</script>

</body>
</html>
""", coins=coins)

# ==========================
# ポーカー（開始）
# ==========================
@app.route("/poker_bot_start", methods=["POST"])
@login_required
def poker_bot_start():
    data = request.json
    bet = int(data.get("bet", 10))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    if bet <= 0:
        conn.close()
        return jsonify({"html": "<p>ベット額が不正です</p>"}), 400

    if bet > coins:
        conn.close()
        return jsonify({"html": f"<p>持ち金が足りません（現在 {coins}）</p>"}), 400

    coins -= bet
    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()
    conn.close()

    deck = generate_deck()
    player_hand = [deck.pop() for _ in range(5)]
    bot_hand = [deck.pop() for _ in range(5)]

    session["poker_deck"] = deck
    session["poker_player_hand"] = player_hand
    session["poker_bot_hand"] = bot_hand
    session["poker_bet"] = bet
    session["poker_pot"] = bet * 2
    session["poker_coins_after_bet"] = coins

    cards_html = ""
    for i, (v, s) in enumerate(player_hand):
        cards_html += f"""
        <div style="display:inline-block; text-align:center; margin:10px;">
            <div class="card">{s} {v}</div>
            <div>
                <label>
                    <input type="checkbox" class="discard-checkbox"> 捨てる
                </label>
            </div>
        </div>
        """

    html = f"""
    <p>コイン: {coins}</p>
    <p>捨てるカードを選んでください</p>

    <div class="row">
        {cards_html}
    </div>

    <button onclick="drawPoker()">交換する</button>
    """

    return jsonify({"html": html})

# ==========================
# ポーカー（交換）
# ==========================
@app.route("/poker_bot_draw", methods=["POST"])
@login_required
def poker_bot_draw():
    data = request.json
    discard_indices = data.get("discard", [])

    deck = session.get("poker_deck", [])
    player_hand = session.get("poker_player_hand", [])
    bot_hand = session.get("poker_bot_hand", [])
    coins = session.get("poker_coins_after_bet", 0)

    discard_indices_sorted = sorted(discard_indices, reverse=True)
    for idx in discard_indices_sorted:
        if 0 <= idx < len(player_hand):
            player_hand.pop(idx)
    while len(player_hand) < 5 and deck:
        player_hand.append(deck.pop())

    bot_discard = bot_discard_indices(bot_hand)
    bot_discard_sorted = sorted(bot_discard, reverse=True)
    for idx in bot_discard_sorted:
        if 0 <= idx < len(bot_hand):
            bot_hand.pop(idx)
    while len(bot_hand) < 5 and deck:
        bot_hand.append(deck.pop())

    session["poker_player_hand"] = player_hand
    session["poker_bot_hand"] = bot_hand
    session["poker_deck"] = deck

    player_cards_html = ""
    for (v, s) in player_hand:
        player_cards_html += f'<div class="card">{s} {v}</div>'

    html = f"""
    <p>コイン: {coins}</p>

    <h3>あなたの最終手札</h3>
    <div class="row">
        {player_cards_html}
    </div>

    <h3>ボットの手札は結果画面で公開されます</h3>

    <button onclick="resultPoker()">結果を見る</button>
    """

    return jsonify({"html": html})

# ==========================
# ポーカー（結果）
# ==========================
@app.route("/poker_bot_result", methods=["POST"])
@login_required
def poker_bot_result():
    player_hand = session.get("poker_player_hand", [])
    bot_hand = session.get("poker_bot_hand", [])
    bet = session.get("poker_bet", 0)
    pot = session.get("poker_pot", 0)

    player_rank, player_name = evaluate_hand(player_hand)
    bot_rank, bot_name = evaluate_hand(bot_hand)

    if player_rank > bot_rank:
        result_text = "あなたの勝ち！"
        winner = "player"
    elif player_rank < bot_rank:
        result_text = "ボットの勝ち…"
        winner = "bot"
    else:
        result_text = "引き分け"
        winner = "draw"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    if winner == "player":
        coins += pot
    elif winner == "draw":
        coins += bet

    if coins < 0:
        coins = 0

    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()
    conn.close()

    player_cards_html = ""
    for (v, s) in player_hand:
        player_cards_html += f'<div class="card">{s} {v}</div>'

    bot_cards_html = ""
    for (v, s) in bot_hand:
        bot_cards_html += f'<div class="card">{s} {v}</div>'

    html = f"""
    <div style="
        background:white;
        padding:40px;
        border-radius:12px;
        box-shadow:0 0 15px rgba(0,0,0,0.1);
        width:90%;
        max-width:600px;
        margin:40px auto;
        text-align:center;
    ">
        <h2>{result_text}</h2>

        <h3>あなたの手札（{player_name}）</h3>
        <div class="row">{player_cards_html}</div>

        <h3>ボットの手札（{bot_name}）</h3>
        <div class="row">{bot_cards_html}</div>

        <p style="font-size:18px; margin-top:20px;">現在のコイン: {coins}</p>
    </div>

    <button onclick="location.href='/games'" style="
        padding:14px;
        font-size:20px;
        background:#28a745;
        color:white;
        border:none;
        border-radius:8px;
        cursor:pointer;
        width:220px;
        display:block;
        margin:20px auto;">
        ゲーム一覧へ戻る
    </button>
    """

    return jsonify({"html": html})

# ==========================
# マイン（未実装）
# ==========================
@app.route("/mines")
@login_required
def mines():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Mines</title>
<style>
    body { font-family: sans-serif; text-align: center; background: #f7f7f7; padding-top: 60px; }
    .container {
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 0 15px rgba(0,0,0,0.1);
        width: 90%;
        max-width: 400px;
        margin: auto;
    }
    button {
        padding: 14px;
        font-size: 18px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        width: 100%;
        margin-top: 20px;
    }
</style>
</head>
<body>

<div class="container">
    <h2>Mines</h2>
    <p>このゲームはまだ準備中です。</p>
    <button onclick="location.href='/games'">ゲーム一覧へ戻る</button>
</div>

</body>
</html>
""")

# ============================
#  Texas Hold'em PART 1 / 5
#  基盤（プレイヤー・デッキ・状態・役判定）
# ============================

# 6人プレイヤー初期化
def init_players():
    return [
        {"id": "you",  "name": "You", "hand": [], "chips": 1000, "bet": 0, "fold": False, "allin": False},
        {"id": "bot1", "name": "Bot1", "hand": [], "chips": 1000, "bet": 0, "fold": False, "allin": False},
        {"id": "bot2", "name": "Bot2", "hand": [], "chips": 1000, "bet": 0, "fold": False, "allin": False},
        {"id": "bot3", "name": "Bot3", "hand": [], "chips": 1000, "bet": 0, "fold": False, "allin": False},
        {"id": "bot4", "name": "Bot4", "hand": [], "chips": 1000, "bet": 0, "fold": False, "allin": False},
        {"id": "bot5", "name": "Bot5", "hand": [], "chips": 1000, "bet": 0, "fold": False, "allin": False},
    ]


# デッキ生成（52枚）
SUITS = ["♠️", "♥️", "♦️", "♣️"]
VALUES = list(range(2, 15))  # 2〜14（14はA）

def generate_deck():
    deck = [(v, s) for v in VALUES for s in SUITS]
    random.shuffle(deck)
    return deck


# ゲーム状態
def init_state():
    return {
        "deck": [],
        "board": [],
        "pot": 0,
        "current_turn": 0,
        "current_bet": 0,
        "round": "preflop",
        "last_raiser": None
    }


# 手札配布（6人 × 2枚）
def deal_hole_cards(players, deck):
    for p in players:
        p["hand"] = [deck.pop(), deck.pop()]


# 場のカード（フロップ・ターン・リバー）
def deal_flop(state):
    state["board"] = [state["deck"].pop(), state["deck"].pop(), state["deck"].pop()]
    state["round"] = "flop"

def deal_turn(state):
    state["board"].append(state["deck"].pop())
    state["round"] = "turn"

def deal_river(state):
    state["board"].append(state["deck"].pop())
    state["round"] = "river"


# ターン進行
def next_turn(state, players):
    n = len(players)
    while True:
        state["current_turn"] = (state["current_turn"] + 1) % n
        if not players[state["current_turn"]]["fold"]:
            break


# 役判定（強化版 evaluate_hand）
def evaluate_hand(hand):
    values = sorted([v for v, s in hand])
    suits = [s for v, s in hand]

    values_ace_high = sorted([14 if v == 1 else v for v in values])
    value_counts = Counter(values_ace_high)
    suit_counts = Counter(suits)

    is_flush = (len(suit_counts) == 1)

    def is_straight(vals):
        return all(vals[i] + 1 == vals[i+1] for i in range(4))

    is_straight_high = is_straight(values_ace_high)

    values_ace_low = sorted([1 if v == 14 else v for v in values_ace_high])
    is_straight_low = is_straight(values_ace_low)

    is_straight_any = is_straight_high or is_straight_low

    counts = sorted(value_counts.values(), reverse=True)

    if is_flush and is_straight_any:
        if set(values_ace_high) == {10, 11, 12, 13, 14}:
            return (10, "ロイヤルストレートフラッシュ", values_ace_high)
        return (9, "ストレートフラッシュ", values_ace_high)

    if counts == [4, 1]:
        return (8, "フォーカード", values_ace_high)

    if counts == [3, 2]:
        return (7, "フルハウス", values_ace_high)

    if is_flush:
        return (6, "フラッシュ", values_ace_high)

    if is_straight_any:
        return (5, "ストレート", values_ace_high)

    if counts == [3, 1, 1]:
        return (4, "スリーカード", values_ace_high)

    if counts == [2, 2, 1]:
        return (3, "ツーペア", values_ace_high)

    if counts == [2, 1, 1, 1]:
        return (2, "ワンペア", values_ace_high)

    return (1, "ハイカード", values_ace_high)


# 7枚 → 最強5枚（best_hand）
def best_hand(cards7):
    best_rank = -1
    best_name = ""
    best_kickers = []

    for comb in itertools.combinations(cards7, 5):
        rank, name, kickers = evaluate_hand(comb)
        if rank > best_rank or (rank == best_rank and kickers > best_kickers):
            best_rank = rank
            best_name = name
            best_kickers = kickers

    return best_rank, best_name, best_kickers
# ============================
#  Texas Hold'em PART 2 / 5
#  ベットラウンド（自由ベット）
# ============================

# プレイヤーの行動を反映する
def player_action(players, state, idx, action, amount=0):
    p = players[idx]
    current_bet = state["current_bet"]
    to_call = current_bet - p["bet"]

    # チェック
    if action == "check":
        return

    # コール
    elif action == "call":
        call_amount = min(to_call, p["chips"])
        p["chips"] -= call_amount
        p["bet"] += call_amount
        state["pot"] += call_amount
        if p["chips"] == 0:
            p["allin"] = True

    # ベット（プリフロップで誰もベットしてない時）
    elif action == "bet":
        bet_amount = min(amount, p["chips"])
        p["chips"] -= bet_amount
        p["bet"] += bet_amount
        state["pot"] += bet_amount
        state["current_bet"] = p["bet"]
        state["last_raiser"] = idx

    # レイズ
    elif action == "raise":
        raise_amount = min(amount, p["chips"])
        p["chips"] -= raise_amount
        p["bet"] += raise_amount
        state["pot"] += raise_amount
        state["current_bet"] = p["bet"]
        state["last_raiser"] = idx

    # フォールド
    elif action == "fold":
        p["fold"] = True

    # オールイン
    elif action == "allin":
        allin_amount = p["chips"]
        p["chips"] = 0
        p["bet"] += allin_amount
        state["pot"] += allin_amount
        state["current_bet"] = max(state["current_bet"], p["bet"])
        state["last_raiser"] = idx
        p["allin"] = True


# ボットの行動（簡易AI）
def bot_action_func(players, state, idx):
    p = players[idx]
    current_bet = state["current_bet"]
    to_call = current_bet - p["bet"]

    import random
    strength = random.random()

    # 強い手 → レイズ
    if strength > 0.85 and p["chips"] > to_call + 20:
        return "raise", to_call + 20

    # 中くらい → コール or チェック
    if strength > 0.4:
        if to_call == 0:
            return "check", 0
        else:
            return "call", 0

    # 弱い → フォールド or チェック
    if to_call == 0:
        return "check", 0
    else:
        return "fold", 0


# ベットラウンド終了判定
def is_betting_round_finished(players, state):
    for p in players:
        if p["fold"]:
            continue
        if p["bet"] != state["current_bet"] and not p["allin"]:
            return False
    return True


# ベットラウンドを1回まわす（対人戦でも使える）
def run_betting_round(players, state, player_action_func, bot_action_func):
    n = len(players)
    state["last_raiser"] = None

    while True:
        idx = state["current_turn"]
        p = players[idx]

        # フォールド or オールインならスキップ
        if p["fold"] or p["allin"]:
            state["current_turn"] = (idx + 1) % n
            continue

        # あなたのターン
        if idx == 0:
            action, amount = player_action_func(players, state)
            player_action(players, state, idx, action, amount)

        # ボットのターン
        else:
            action, amount = bot_action_func(players, state, idx)
            player_action(players, state, idx, action, amount)

        # ラウンド終了？
        if is_betting_round_finished(players, state):
            break

        # 次のプレイヤーへ
        state["current_turn"] = (idx + 1) % n

    # ラウンド終了後、次ラウンド用に bet をリセット
    for p in players:
        p["bet"] = 0

    state["current_bet"] = 0
# ============================
#  Texas Hold'em PART 3 / 5
#  ショーダウン（勝者判定＋総取り＋DB反映）
# ============================

def holdem_showdown(players, state):
    results = []

    # フォールドしていないプレイヤーの役を判定
    for p in players:
        if p["fold"]:
            continue

        cards7 = p["hand"] + state["board"]
        rank, name, kickers = best_hand(cards7)
        results.append((rank, name, kickers, p))

    # 勝者決定（rank → kicker の順で比較）
    winner = max(results, key=lambda x: (x[0], x[2]))
    win_rank, win_name, win_kickers, win_player = winner

    # 総取り
    win_player["chips"] += state["pot"]

    # Supabase の users テーブルに反映（人間のみ）
    # bot は DB に書かない
    if not win_player["id"].startswith("bot"):
        supabase.table("users").update({
            "coins": win_player["chips"]
        }).eq("id", win_player["id"]).execute()

    # 結果画面（HTML）
    html = f"""
    <h2>勝者: {win_player['name']}（{win_name}）</h2>
    <p>獲得チップ: {state['pot']}</p>

    <h3>最強の5枚</h3>
    <div class="row">
        {"".join([f'<div class="card">{s} {v}</div>' for (v, s) in win_player["hand"]])}
    </div>

    <button id="backBtn" onclick="location.href='/games'">ゲーム一覧へ戻る</button>
    """

    return html
# ============================
#  Texas Hold'em PART 4 / 5
#  対人戦API（部屋作成・参加・開始・行動）
# ============================

# Supabase クライアント

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase = create_client(supabase_url, supabase_key)

# ----------------------------------------
# 部屋作成
# ----------------------------------------
@app.route("/holdem_room_create", methods=["POST"])
@login_required
def holdem_room_create():
    user_id = current_user.id

    players = [
        {
            "id": user_id,
            "name": current_user.username,
            "chips": current_user.coins,
            "bet": 0,
            "fold": False,
            "allin": False,
            "hand": []
        }
    ]

    state = {
        "deck": [],
        "board": [],
        "pot": 0,
        "current_turn": 0,
        "current_bet": 0,
        "round": "waiting",
        "last_raiser": None
    }

    room = supabase.table("rooms").insert({
        "players": players,
        "state": state
    }).execute()

    room_id = room.data[0]["id"]

    return jsonify({
        "room_id": room_id,
        "message": "部屋を作成しました。友達に部屋IDを共有してください。"
    })


# ----------------------------------------
# 部屋参加
# ----------------------------------------
@app.route("/holdem_room_join", methods=["POST"])
@login_required
def holdem_room_join():
    data = request.json
    room_id = data.get("room_id")
    user_id = current_user.id

    room = supabase.table("rooms").select("*").eq("id", room_id).execute()
    if not room.data:
        return jsonify({"error": "部屋が存在しません"}), 400

    room_data = room.data[0]
    players = room_data["players"]

    # すでに参加している？
    for p in players:
        if p["id"] == user_id:
            return jsonify({"message": "すでに参加しています"})

    # 6人以上は不可
    if len(players) >= 6:
        return jsonify({"error": "満員です"}), 400

    players.append({
        "id": user_id,
        "name": current_user.username,
        "chips": current_user.coins,
        "bet": 0,
        "fold": False,
        "allin": False,
        "hand": []
    })

    supabase.table("rooms").update({
        "players": players
    }).eq("id", room_id).execute()

    return jsonify({
        "message": "部屋に参加しました",
        "players": players
    })


# ----------------------------------------
# ボット追加（6人になるまで）
# ----------------------------------------
@app.route("/holdem_room_add_bots", methods=["POST"])
@login_required
def holdem_room_add_bots():
    data = request.json
    room_id = data.get("room_id")

    room = supabase.table("rooms").select("*").eq("id", room_id).execute()
    if not room.data:
        return jsonify({"error": "部屋が存在しません"}), 400

    room_data = room.data[0]
    players = room_data["players"]

    bot_count = 1
    while len(players) < 6:
        players.append({
            "id": f"bot{bot_count}",
            "name": f"Bot{bot_count}",
            "chips": 1000,
            "bet": 0,
            "fold": False,
            "allin": False,
            "hand": []
        })
        bot_count += 1

    supabase.table("rooms").update({
        "players": players
    }).eq("id", room_id).execute()

    return jsonify({"message": "ボットを追加しました", "players": players})


# ----------------------------------------
# ゲーム開始（手札配布）
# ----------------------------------------
@app.route("/holdem_room_start", methods=["POST"])
@login_required
def holdem_room_start():
    data = request.json
    room_id = data.get("room_id")

    room = supabase.table("rooms").select("*").eq("id", room_id).execute()
    if not room.data:
        return jsonify({"error": "部屋が存在しません"}), 400

    room_data = room.data[0]
    players = room_data["players"]

    if len(players) < 2:
        return jsonify({"error": "プレイヤーが足りません"}), 400

    deck = generate_deck()

    for p in players:
        p["hand"] = [deck.pop(), deck.pop()]
        p["bet"] = 0
        p["fold"] = False
        p["allin"] = False

    state = {
        "deck": deck,
        "board": [],
        "pot": 0,
        "current_turn": 0,
        "current_bet": 0,
        "round": "preflop",
        "last_raiser": None
    }

    supabase.table("rooms").update({
        "players": players,
        "state": state
    }).eq("id", room_id).execute()

    return jsonify({"message": "ゲームを開始しました"})


# ----------------------------------------
# 部屋状態取得（ポーリング用）
# ----------------------------------------
@app.route("/holdem_room_status", methods=["POST"])
@login_required
def holdem_room_status():
    data = request.json
    room_id = data.get("room_id")

    room = supabase.table("rooms").select("*").eq("id", room_id).execute()
    if not room.data:
        return jsonify({"error": "部屋が存在しません"}), 400

    return jsonify(room.data[0])


# ----------------------------------------
# 行動（対人戦＋ボット混合）
# ----------------------------------------
@app.route("/holdem_action_room", methods=["POST"])
@login_required
def holdem_action_room():
    data = request.json
    room_id = data.get("room_id")
    action = data.get("action")
    amount = int(data.get("amount", 0))

    user_id = current_user.id

    room = supabase.table("rooms").select("*").eq("id", room_id).execute()
    if not room.data:
        return jsonify({"error": "部屋が存在しません"}), 400

    room_data = room.data[0]
    players = room_data["players"]
    state = room_data["state"]

    # 自分のインデックス
    idx = next((i for i, p in enumerate(players) if p["id"] == user_id), None)
    if idx is None:
        return jsonify({"error": "この部屋に参加していません"}), 400

    # 自分のターンでなければ行動不可
    if state["current_turn"] != idx:
        return jsonify({"error": "あなたのターンではありません"}), 400

    # あなたの行動
    player_action(players, state, idx, action, amount)

    # 次のターンへ
    state["current_turn"] = (state["current_turn"] + 1) % len(players)

    # 🔥 ボットのターンなら自動行動
    while players[state["current_turn"]]["id"].startswith("bot"):
        bot_idx = state["current_turn"]
        bot_act, bot_amount = bot_action_func(players, state, bot_idx)
        player_action(players, state, bot_idx, bot_act, bot_amount)

        state["current_turn"] = (state["current_turn"] + 1) % len(players)

        if is_betting_round_finished(players, state):
            break

    # ベットラウンド終了？
    if is_betting_round_finished(players, state):
        if state["round"] == "preflop":
            deal_flop(state)
        elif state["round"] == "flop":
            deal_turn(state)
        elif state["round"] == "turn":
            deal_river(state)
        elif state["round"] == "river":
            html = holdem_showdown(players, state)
            supabase.table("rooms").update({
                "players": players,
                "state": state
            }).eq("id", room_id).execute()
            return jsonify({"html": html})

        # ベット額リセット
        for p in players:
            p["bet"] = 0
        state["current_bet"] = 0
        state["last_raiser"] = None

    # Supabase に保存
    supabase.table("rooms").update({
        "players": players,
        "state": state
    }).eq("id", room_id).execute()

    html = holdem_render(players, state)
    return jsonify({"html": html})

# ============================
#  Texas Hold'em PART 5 / 5
#  対人戦UI（リアルタイム更新＋行動送信）
# ============================

@app.route("/holdem_room")
@login_required
def holdem_room():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Texas Hold'em 対人戦</title>

<style>
    body {
        font-family: sans-serif;
        background: #f7f7f7;
        text-align: center;
        padding-top: 40px;
    }
    .card {
        font-size: 32px;
        background: white;
        padding: 15px 25px;
        border-radius: 12px;
        display: inline-block;
        margin: 10px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2);
    }
    .row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        margin-top: 20px;
        flex-wrap: wrap;
    }
    button {
        padding: 14px;
        font-size: 20px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        width: 220px;
        margin-top: 10px;
    }
    #backBtn {
        background: #28a745;
        margin-top: 20px;
    }
</style>
</head>
<body>

<h2>Texas Hold'em 対人戦（最大6人）</h2>

<div id="setupArea">
    <p>部屋IDを入力して参加するか、新しい部屋を作成してください。</p>

    <input id="roomIdInput" type="text" placeholder="room_id" style="padding:10px;font-size:18px;">
    <button onclick="joinRoom()">部屋に参加</button>

    <button onclick="createRoom()">新しい部屋を作成</button>

    <button id="backBtn" onclick="location.href='/games'">ゲーム一覧へ戻る</button>
</div>

<div id="gameArea" style="margin-top:40px;"></div>

<script>
let room_id = null;

// ------------------------------
// 部屋作成
// ------------------------------
async function createRoom() {
    const res = await fetch("/holdem_room_create", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({})
    });
    const data = await res.json();
    room_id = data.room_id;

    document.getElementById("setupArea").innerHTML = `
        <p>部屋を作成しました。</p>
        <p>部屋ID: <b>${room_id}</b></p>
        <p>友達に共有してください。</p>
        <button onclick="addBots()">ボット追加（6人にする）</button>
        <button onclick="startPolling()">ゲーム画面へ</button>
    `;
}

// ------------------------------
// 部屋参加
// ------------------------------
async function joinRoom() {
    room_id = document.getElementById("roomIdInput").value;
    if (!room_id) return;

    const res = await fetch("/holdem_room_join", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ room_id })
    });
    const data = await res.json();

    document.getElementById("setupArea").innerHTML = `
        <p>部屋に参加しました。</p>
        <p>部屋ID: <b>${room_id}</b></p>
        <button onclick="startPolling()">ゲーム画面へ</button>
    `;
}

// ------------------------------
// ボット追加
// ------------------------------
async function addBots() {
    const res = await fetch("/holdem_room_add_bots", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ room_id })
    });
    const data = await res.json();
    alert("ボットを追加しました（最大6人）");
}

// ------------------------------
// ポーリング開始
// ------------------------------
function startPolling() {
    document.getElementById("gameArea").innerHTML = "<p>読み込み中...</p>";

    // ゲーム開始（手札配布）
    fetch("/holdem_room_start", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ room_id })
    });

    setInterval(async () => {
        const res = await fetch("/holdem_room_status", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ room_id })
        });

        const data = await res.json();
        renderGame(data.players, data.state);
    }, 1000);
}

// ------------------------------
// 行動送信
// ------------------------------
async function sendAction(action, amount=0) {
    const res = await fetch("/holdem_action_room", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ room_id, action, amount })
    });

    const data = await res.json();
    document.getElementById("gameArea").innerHTML = data.html;
}

// ------------------------------
// 画面描画
// ------------------------------
function renderGame(players, state) {
    if (!players || !state) return;

    let yourHand = "";
    let board = "";
    let others = "";

    // あなたの手札
    const me = players.find(p => p.id === "{{ current_user.id }}");
    if (me && me.hand.length > 0) {
        yourHand = me.hand.map(c => `<div class="card">${c[1]} ${c[0]}</div>`).join("");
    }

    // 場のカード
    if (state.board.length > 0) {
        board = state.board.map(c => `<div class="card">${c[1]} ${c[0]}</div>`).join("");
    } else {
        board = "<p>まだ場のカードはありません</p>";
    }

    // 他プレイヤー
    others = players.map(p => {
        if (p.id === "{{ current_user.id }}") return "";
        return `
            <div class="card">
                ${p.name}<br>
                chips: ${p.chips}<br>
                ${p.fold ? "FOLD" : ""}
            </div>
        `;
    }).join("");

    document.getElementById("gameArea").innerHTML = `
        <h3>あなたの手札</h3>
        <div class="row">${yourHand}</div>

        <h3>場のカード</h3>
        <div class="row">${board}</div>

        <h3>プレイヤー一覧</h3>
        <div class="row">${others}</div>

        <h3>ポット: ${state.pot}</h3>

        <div id="actionArea">
            <button onclick="sendAction('check')">チェック</button>
            <button onclick="sendAction('call')">コール</button>

            <p>ベット額: <input id="betAmount" type="number" value="10" min="1" style="width:80px;"></p>
            <button onclick="sendAction('bet', Number(document.getElementById('betAmount').value))">ベット</button>

            <p>レイズ額: <input id="raiseAmount" type="number" value="20" min="1" style="width:80px;"></p>
            <button onclick="sendAction('raise', Number(document.getElementById('raiseAmount').value))">レイズ</button>

            <button onclick="sendAction('fold')">フォールド</button>
            <button onclick="sendAction('allin')">オールイン</button>
        </div>
    `;
}
</script>

</body>
</html>
""")

# ==========================
# ログアウト
# ==========================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# ==========================
# アプリ起動
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
