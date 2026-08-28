from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import random
import psycopg2
from psycopg2 import pool
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
# DB 接続プール（Supabase / PostgreSQL）
# ==========================
db_pool = pool.SimpleConnectionPool(
    1, 15,
    host="aws-0-ap-northeast-1.pooler.supabase.com",
    database="postgres",
    user="postgres.txfrrpxosbhytshmwzkq",
    password="nosuke0411!",
    port=5432
)

def get_conn():
    return db_pool.getconn()

def put_conn(conn):
    db_pool.putconn(conn)

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
    cur.close()
    put_conn(conn)
    if row:
        return User(row[0], row[1], row[2], row[3])
    return None

def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, coins FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    put_conn(conn)
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
    base_sh = "https://m.youtube.com/shorts/"

    if url.startswith(base_short):
        return url
    if url.startswith(base_mobile):
        video_id = url[len(base_mobile):]
        return f"https://youtu.be/{video_id}"
    if url.startswith(base_pc):
        video_id = url[len(base_pc):]
        return f"https://youtu.be/{video_id}"
    if url.startswith(base_sh):
        video_id = url[len(base_sh):]
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
        padding: 14px;
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
            cur.close()
            put_conn(conn)
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

        cur.close()
        put_conn(conn)
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

    html, body {
        height: 100%;
        margin: 0;
        padding: 0;
        overflow: hidden;
        background: #0d0d0d;
        font-family: sans-serif;
    }

    /* 上部タイトル */
    .title-bar {
        text-align: center;
        font-size: 32px;
        font-weight: 700;
        color: white;
        padding-top: 20px;
        letter-spacing: 0.05em;
    }

    /* 設定ボタン */
    .top-bar {
        display: flex;
        justify-content: flex-end;
        padding: 20px;
        position: absolute;
        top: 0;
        right: 0;
        left: 0;
    }

    .settings-btn {
        width: 32px;
        height: 32px;
        cursor: pointer;
    }

    /* 横スクロール */
    .game-scroll {
        position: absolute;
        top: 55%; /* タイトル分だけ下げる */
        left: 0;
        right: 0;
        transform: translateY(-50%);
        display: flex;
        overflow-x: auto;
        gap: 24px;
        padding: 0 20px;
        scroll-snap-type: x mandatory;
    }

    /* ボタン */
    .game-btn {
        flex: 0 0 auto;
        width: 180px;
        height: 120px;
        border-radius: 12px;
        border: none;
        cursor: pointer;
        background: #222;
        color: white;
        font-size: 18px;
        font-weight: 600;
        display: flex;
        justify-content: center;
        align-items: center;
        scroll-snap-align: center;
        transition: 0.2s;
        text-decoration: none;
    }

    .game-btn:hover {
        background: #333;
        transform: translateY(-4px);
    }

    /* 色テーマ */
    .slot { background: #ff5f6d; }
    .highlow { background: #36d1dc; }
    .ranking { background: #f6d365; }
    .chat { background: #a1c4fd; }
    .revive { background: #96e6a1; }
    .transfer { background: #8e44ad; }

    /* 設定ポップアップ */
    .popup {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.6);
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .popup-content {
        background: #111;
        padding: 20px;
        border-radius: 12px;
        width: 260px;
        text-align: center;
        color: white;
        position: relative;
    }

    .close-btn {
        position: absolute;
        top: 10px;
        right: 10px;
        background: none;
        border: none;
        color: white;
        font-size: 22px;
        cursor: pointer;
    }

    .menu-btn {
        display: block;
        background: #444;
        padding: 10px;
        margin: 10px 0;
        border-radius: 8px;
        text-decoration: none;
        color: white;
    }

    .logout {
        background: #b00000;
    }

    .hidden {
        display: none;
    }

</style>
</head>
<body>

<div class="title-bar">機能一覧</div>

<div class="top-bar">
    <img src="{{ url_for('static', filename='settei.webp') }}" class="settings-btn" id="settings-btn">
</div>

<div class="game-scroll">

    <a href="/slot" class="game-btn slot">スロット</a>

    <a href="/highlow" class="game-btn highlow">ハイロー</a>

    <a href="/ranking" class="game-btn ranking">ランキング</a>

    <a href="/chat" class="game-btn chat">チャット</a>

    <a href="/transfer" class="game-btn transfer">コイン譲渡</a>

    {% if current_user.coins == 0 %}
    <a href="/revive_game" class="game-btn revive">復活ゲー</a>
    {% endif %}

</div>

<div id="settings-popup" class="popup hidden">
    <div class="popup-content">
        <button class="close-btn">×</button>
        <h2>メニュー</h2>
        <a href="/" class="menu-btn">変換ツールへ</a>
        <a href="/logout" class="menu-btn logout">ログアウト</a>
    </div>
</div>

<script>
document.getElementById("settings-btn").onclick = () => {
    document.getElementById("settings-popup").classList.remove("hidden");
};

document.querySelector(".close-btn").onclick = () => {
    document.getElementById("settings-popup").classList.add("hidden");
};
</script>

</body>
</html>
""")

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
    cur.close()
    put_conn(conn)
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
        cur.close()
        put_conn(conn)
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

    cur.close()
    put_conn(conn)

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
    suit = random.choice(["S", "H", "D", "C"])  # ← 絵文字はPythonで壊れるので安全化
    return value, suit

suit_map = {"S": "♠️", "H": "♥️", "D": "♦️", "C": "♣️"}

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
    suit_emoji = suit_map[suit]

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
        <div class="card">{{ suit_emoji }} {{ value }}</div>
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
""", coins=coins, value=value, suit=suit, suit_emoji=suit_emoji)

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
        cur.close()
        put_conn(conn)
        return jsonify({"html": """
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
        """}), 400

    if bet > coins:
        cur.close()
        put_conn(conn)
        return jsonify({"html": f"""
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
        """}), 400

    coins -= bet
    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()

    cur.close()
    put_conn(conn)

    multiplier = 1.0
    suit_emoji = suit_map[current_suit]

    html = f"""
    <p>コイン: {coins}</p>

    <div class="row">
        <div class="card">{suit_emoji} {current_value}</div>
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
    suit_emoji1 = suit_map[current_suit]
    suit_emoji2 = suit_map[next_suit]

    # 引き分け
    if next_value == current_value:
        html = f"""
        <h2>引き分け！</h2>

        <div class="row">
            <div class="card">{suit_emoji1} {current_value}</div>
            <div class="card">{suit_emoji2} {next_value}</div>
        </div>

        <p>累積倍率: {multiplier}</p>

        <button onclick="play('high', {next_value}, '{next_suit}', {bet}, {multiplier})">High</button><br>
        <button onclick="play('low', {next_value}, '{next_suit}', {bet}, {multiplier})">Low</button><br>

    <button onclick="this.disabled=true; setTimeout('this.disabled=false', 3000); location.href='/highlow_cashout?bet=10&multiplier=2.5'">
        やめる（払い戻し）
    </button>



        <button onclick="location.href='/games'">ゲーム一覧へ</button>
        """
        return jsonify({"html": html})

    # 勝敗判定
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
        <div class="card">{suit_emoji1} {current_value}</div>
        <div class="card">{suit_emoji2} {next_value}</div>
    </div>

    <p>累積倍率: {round(multiplier,3)}</p>

    <button onclick="play('high', {next_value}, '{next_suit}', {bet}, {multiplier})">High</button><br>
    <button onclick="play('low', {next_value}, '{next_suit}', {bet}, {multiplier})">Low</button><br>

    <button onclick="this.disabled=true; setTimeout('this.disabled=false', 3000); location.href='/highlow_cashout?bet=10&multiplier=2.5'">
        やめる（払い戻し）
    </button>

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

    cur.close()
    put_conn(conn)

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

#==========================
#復活ゲーム
#==========================
@app.route("/revive_game")
@login_required
def revive_game():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>復活ゲーム</title>
<style>
    body { text-align:center; font-family:sans-serif; padding-top:40px; }
    .box {
        display:inline-block;
        padding:20px;
        border:2px solid #333;
        border-radius:10px;
        margin:10px;
        font-size:32px;
        width:120px;
    }
    button {
        padding:14px 30px;
        font-size:20px;
        border:none;
        background:#007bff;
        color:white;
        border-radius:8px;
        cursor:pointer;
        margin-top:20px;
    }
</style>
</head>
<body>

<h2>復活ゲーム（乱数で復活コインを決めよう）</h2>

<div>
    <div class="box" id="left">?</div>
    <span style="font-size:32px;">×</span>
    <div class="box" id="right">?</div>
</div>

<p style="font-size:24px; margin-top:20px;">復活コイン: <span id="result">0</span></p>

<button id="startBtn" onclick="startGame()">スタート</button>
<button id="stopBtn" onclick="stopGame()" style="display:none;">ストップ</button>
<button id="backBtn" onclick="location.href='/games'" style="display:none;">ゲーム一覧へ戻る</button>

<script>
let intervalId = null;
let finalResult = 0;

function startGame() {
    document.getElementById("startBtn").style.display = "none";
    document.getElementById("stopBtn").style.display = "inline-block";

    intervalId = setInterval(() => {
        let left = Math.floor(Math.random() * 100) + 1;
        let right = Math.floor(Math.random() * 100) + 1;
        finalResult = left * right;

        document.getElementById("left").innerText = left;
        document.getElementById("right").innerText = right;
        document.getElementById("result").innerText = finalResult;
    }, 80);
}

function stopGame() {
    clearInterval(intervalId);

    document.getElementById("stopBtn").style.display = "none";
    document.getElementById("backBtn").style.display = "inline-block";

    fetch("/revive", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        credentials: "include",
        body:JSON.stringify({ score: finalResult })
    }).then(r => r.json()).then(data => {
        alert(finalResult + " コイン復活しました！");
    });
}
</script>

</body>
</html>
""")

@app.route("/revive", methods=["POST"])
@login_required
def revive():
    data = request.json
    score = int(data.get("score", 0))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET coins = %s WHERE id = %s", (score, current_user.id))
    conn.commit()
    cur.close()
    put_conn(conn)

    return jsonify({"coins": score})

#==========================
#ランキング
#==========================
@app.route("/ranking")
@login_required
def ranking():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, username, coins FROM users ORDER BY coins DESC")
    rows = cur.fetchall()

    cur.close()
    put_conn(conn)

    users = [User(r[0], r[1], None, r[2]) for r in rows]
    top10 = users[:10]
    my_rank = next((i + 1 for i, u in enumerate(users) if u.id == current_user.id), None)

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Ranking</title>
<style>

    html, body {
        height: 100%;
        margin: 0;
        padding: 0;
        overflow: hidden;
    }

    body {
        font-family: sans-serif;
        background-image: url('{{ url_for('static', filename='haikei_2.webp') }}');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        color: white;
        text-align: center;
    }

    .container {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -55%);
        background: rgba(0,0,0,0.55);
        padding: 20px;
        border-radius: 12px;
        width: 90%;
        max-width: 450px;
        height: 60vh;
        overflow-y: auto;
    }

    .rank-item {
        background: rgba(255,255,255,0.1);
        padding: 10px;
        margin: 6px 0;
        border-radius: 8px;
        font-size: 18px;
    }

    .back-btn {
        position: absolute;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        background: #444;
        padding: 12px 20px;
        border-radius: 8px;
        text-decoration: none;
        color: white;
        font-size: 18px;
    }

</style>
</head>
<body>

<div class="container">
    <h2>総資産ランキング</h2>

    {% for u in top10 %}
        <div class="rank-item">
            {{ loop.index }} 位：{{ u.username }}（{{ u.coins }} コイン）
        </div>
    {% endfor %}

    <hr style="margin: 20px 0; opacity: 0.4;">

    <div class="rank-item">
        あなたの順位：{{ my_rank }} 位（{{ current_user.coins }} コイン）
    </div>
</div>

<a href="/games" class="back-btn">ゲーム一覧に戻る</a>

</body>
</html>
""", top10=top10, my_rank=my_rank)

#==========================
#チャット
#==========================
@app.route("/chat")
@login_required
def chat():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Chat</title>
<style>

body {
    height: 100vh;
    margin: 0;
    padding: 0;
    font-family: sans-serif;
    background: #1e1e1e;
    color: white;
    text-align: center;
    overflow-y: auto;
}

.chat-box {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -55%);
    background: #2b2b2b;
    width: 90%;
    max-width: 500px;
    height: 65vh;
    padding: 20px;
    border-radius: 16px;
    overflow-y: auto;
    font-size: 20px;
}

.input-area {
    position: absolute;
    bottom: 90px;
    left: 50%;
    transform: translateX(-50%);
    width: 90%;
    max-width: 500px;
    display: flex;
}

input {
    flex: 1;
    padding: 14px;
    border-radius: 10px;
    border: none;
    font-size: 18px;
}

button {
    margin-left: 12px;
    padding: 14px 20px;
    border-radius: 10px;
    border: none;
    background: #444;
    color: white;
    font-size: 18px;
}

.home-btn {
    position: absolute;
    bottom: 25px;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    padding: 14px 22px;
    border-radius: 10px;
    color: white;
    text-decoration: none;
    font-size: 20px;
}

.chat-message {
    display: flex;
    text-align: left;
    margin-bottom: 12px;
}

.chat-username {
    width: 9em;
    font-weight: bold;
    font-size: 18px;
}

.chat-text {
    font-size: 18px;
    flex: 1;
}

</style>
</head>
<body>

<div class="chat-box" id="chat-box"></div>

<div class="input-area">
    <input id="msg" placeholder="メッセージを入力">
    <button id="send-btn" onclick="sendMsg()">送信</button>
</div>

<a href="/games" class="home-btn">ホーム画面に戻る</a>

<script>
let sending = false;
const myName = "{{ current_user.username }}";

function loadChat() {
    fetch('/chat_load')
        .then(res => res.json())
        .then(data => {
            let box = document.getElementById("chat-box");

            box.innerHTML = "";

            data.forEach(m => {
                box.innerHTML += `
                    <div class="chat-message">
                        <div class="chat-username">${m.username}：</div>
                        <div class="chat-text">${m.message}</div>
                    </div>
                `;
            });

            box.scrollTop = box.scrollHeight;

            if (data.length > 0) {
                let last = data[data.length - 1];
                if (last.username === myName) {
                    sending = false;
                    document.getElementById("send-btn").disabled = false;
                }
            }
        });
}

function sendMsg() {
    if (sending) return;

    let msg = document.getElementById("msg").value;
    if (!msg.trim()) return;

    sending = true;
    document.getElementById("send-btn").disabled = true;

    fetch('/chat_send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg})
    }).then(() => {
        document.getElementById("msg").value = "";
    });
}

setInterval(loadChat, 800);
loadChat();

</script>

</body>
</html>
""")

@app.route("/chat_load")
@login_required
def chat_load():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, message FROM chat ORDER BY id ASC")
    rows = cur.fetchall()

    cur.close()
    put_conn(conn)

    return jsonify([
        {"id": r[0], "username": r[1], "message": r[2]}
        for r in rows
    ])

@app.route("/chat_send", methods=["POST"])
@login_required
def chat_send():
    data = request.json
    msg = data.get("message")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat (user_id, username, message) VALUES (%s, %s, %s)",
        (current_user.id, current_user.username, msg)
    )
    conn.commit()

    cur.close()
    put_conn(conn)

    return jsonify({"status": "ok"})
#==========================
#ギフト
#==========================
@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    message = ""

    if request.method == "POST":
        target_name = request.form.get("target")
        amount_raw = request.form.get("amount")

        # 入力チェック
        if not amount_raw:
            message = "コイン数を入力してください"
            return render_template_string(transfer_html, message=message)

        try:
            amount = int(amount_raw)
        except:
            message = "コイン数は数字で入力してください"
            return render_template_string(transfer_html, message=message)

        # 自分に送れない
        if target_name == current_user.username:
            message = "自分に送ることはできません"
            return render_template_string(transfer_html, message=message)

        conn = get_conn()
        cur = conn.cursor()

        # 送り先ユーザー取得
        cur.execute("SELECT id, coins FROM users WHERE username=%s", (target_name,))
        row = cur.fetchone()

        if not row:
            cur.close()
            put_conn(conn)
            message = "ユーザーが存在しません"
            return render_template_string(transfer_html, message=message)

        target_id, target_coins = row

        # コイン不足
        if current_user.coins < amount:
            cur.close()
            put_conn(conn)
            message = "コインが足りません"
            return render_template_string(transfer_html, message=message)

        # 送る側のコイン減算
        cur.execute("UPDATE users SET coins = coins - %s WHERE id=%s", (amount, current_user.id))

        # 受け取る側のコイン加算
        cur.execute("UPDATE users SET coins = coins + %s WHERE id=%s", (amount, target_id))

        conn.commit()
        cur.close()
        put_conn(conn)

        message = f"{target_name} に {amount} コイン送ったよ！"

    return render_template_string(transfer_html, message=message)


transfer_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>コイン譲渡</title>
<style>
body {
    background: #ffffff;
    color: #333;
    font-family: sans-serif;
    margin: 0;
    padding: 0;

    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}

.container {
    background: #f5f5f5;
    padding: 30px;
    border-radius: 12px;
    width: 300px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

input, button {
    padding: 10px;
    margin: 10px 0;
    width: 90%;
    border-radius: 8px;
    border: 1px solid #ccc;
}

button {
    background: #36d1dc;
    cursor: pointer;
    font-weight: bold;
    border: none;
}
button:hover {
    background: #5b86e5;
}

.back-btn {
    background: #444;
    color: white;
    margin-top: 15px;
}
.back-btn:hover {
    background: #666;
}

.message {
    margin-top: 15px;
    font-weight: bold;
    color: #d00000;
}
</style>
</head>
<body>

<div class="container">
    <h2>コイン譲渡</h2>

    <form method="POST">
        <input type="text" name="target" placeholder="送り先ユーザー名" required>
        <input type="number" name="amount" min="1" placeholder="送るコイン数" required>
        <button type="submit">送る</button>
    </form>

    <div class="message">{{ message }}</div>

    <a href="/games">
        <button class="back-btn">ゲーム一覧へ戻る</button>
    </a>
</div>

</body>
</html>
"""

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
