from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import time, math, random
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

    <a href="/highlow" class="game-btn highlow">ハイロー</a>

    <a href="/crash" class="game-btn crash">クラッシュ</a>

    <a href="/ranking" class="game-btn ranking">ランキング</a>

    <a href="https://chat.onl.jp/?ZV5qqFKWMj" class="game-btn chat" target="_blank">チャット</a>

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

async function play(choice) {
    const res = await fetch("/highlow_play2", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ choice })
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

    if bet <= 0 or bet > coins:
        cur.close()
        put_conn(conn)
        return jsonify({"html": "<p>ベット額が不正です</p>"}), 400

    # コインを引く
    coins -= bet
    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()
    cur.close()
    put_conn(conn)

    # ★ session に保存（重要）
    session["hl_bet"] = bet
    session["hl_multiplier"] = 1.0
    session["hl_current_value"] = current_value
    session["hl_current_suit"] = current_suit

    suit_emoji = suit_map[current_suit]

    html = f"""
    <p>コイン: {coins}</p>

    <div class="row">
        <div class="card">{suit_emoji} {current_value}</div>
        <div class="card">？</div>
    </div>

    <p>累積倍率: 1.0</p>

    <button onclick="play('high')">High</button><br>
    <button onclick="play('low')">Low</button><br>

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

    # ★ session から正しい値を取得
    current_value = session.get("hl_current_value")
    current_suit = session.get("hl_current_suit")
    bet = session.get("hl_bet")
    multiplier = session.get("hl_multiplier")

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

        <button onclick="play('high')">High</button><br>
        <button onclick="play('low')">Low</button><br>

        <button id="cashout_btn"
onclick="document.getElementById('cashout_btn').disabled=true;
setTimeout('document.getElementById(\\'cashout_btn\\').disabled=false', 3000);
location.href='/highlow_cashout'">
            やめる（払い戻し）
        </button>

        <button onclick="location.href='/games'">ゲーム一覧へ</button>
        """

        # ★ 次のカードを session に保存
        session["hl_current_value"] = next_value
        session["hl_current_suit"] = next_suit

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

    # ★ multiplier を更新
    session["hl_multiplier"] = multiplier
    session["hl_current_value"] = next_value
    session["hl_current_suit"] = next_suit

    html = f"""
    <h2>{result_text}</h2>

    <div class="row">
        <div class="card">{suit_emoji1} {current_value}</div>
        <div class="card">{suit_emoji2} {next_value}</div>
    </div>

    <p>累積倍率: {round(multiplier,3)}</p>

    <button onclick="play('high')">High</button><br>
    <button onclick="play('low')">Low</button><br>

    <button id="cashout_btn"
onclick="document.getElementById('cashout_btn').disabled=true;
setTimeout('document.getElementById(\\'cashout_btn\\').disabled=false', 3000);
location.href='/highlow_cashout'">
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
    bet = session.get("hl_bet")
    multiplier = session.get("hl_multiplier")

    payout = int(bet * multiplier)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    coins += payout
    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()

    cur.close()
    put_conn(conn)

    session.pop("hl_bet", None)
    session.pop("hl_multiplier", None)
    session.pop("hl_current_value", None)
    session.pop("hl_current_suit", None)

    return f"""
    <style>
        .card {{
            font-size:50px;
            background:white;
            padding:25px 40px;
            border-radius:12px;
            display:inline-block;
            margin:10px;
            box-shadow:0 0 15px rgba(0,0,0,0.2);
        }}
        .row {{
            display:flex;
            justify-content:center;
            align-items:center;
            gap:40px;
            margin-top:30px;
        }}
    </style>

    <div style="text-align:center; padding-top:40px;">

        <h2>払い戻し</h2>

        <div class="row">
            <div class="card">+{payout} コイン</div>
        </div>

        <p style="font-size:18px;">現在のコイン: {coins}</p>

        <button onclick="location.href='/games'" 
            style="padding:14px; font-size:20px; background:#28a745; color:white; border:none; border-radius:8px; cursor:pointer; width:200px; display:block; margin:20px auto;">
            ゲーム一覧へ戻る
        </button>
    </div>
    """

# ==========================
# クラッシュ（指数分布でクラッシュポイント生成）
# ==========================
def random_exponential(lambda_=1):
    return -math.log(1 - random.random()) / lambda_

def generate_crash_point():
    return 1.0 + random_exponential() * 8


# ==========================
# クラッシュ（倍率計算）← ハイローと衝突しないようにリネーム
# ==========================
def crash_calc_multiplier(start_time):
    elapsed = time.time() - start_time
    return 1.0 + (elapsed ** 1.3)


#==========================
#クラッシュ
#==========================
@app.route("/crash")
@login_required
def crash():
    coins = current_user.coins

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Crash Game</title>

<style>
    body {
        font-family:sans-serif;
        background:#f7f7f7;
        text-align:center;
        padding-top:40px;
    }
    #multiplier {
        font-size:70px;
        font-weight:bold;
        transition:color 0.2s, transform 0.2s;
    }
    .green { color:#28a745; }
    .yellow { color:#ffc107; }
    .red { color:#dc3545; }

    button {
        padding:14px;
        font-size:22px;
        background:#007bff;
        color:white;
        border:none;
        border-radius:8px;
        cursor:pointer;
        margin-top:20px;
        width:200px;
    }
    #startBtn { background:#28a745; }
    #backBtn { background:#6c757d; margin-top:30px; }
</style>
</head>
<body>

<h2>Crash Game</h2>
<p>コイン: {{ coins }}</p>

<p>
    ベット額:
    <input id="bet" type="number" value="10" min="1" style="width:80px; font-size:18px;">
</p>

<div id="multiplier" class="green">1.00x</div>

<button id="startBtn">開始</button>
<button id="cashoutBtn" disabled>逃げる！</button>

<div id="history">履歴: 読み込み中...</div>

<button id="backBtn" onclick="location.href='/games'">ゲーム一覧へ戻る</button>

<script>
let crash_interval = null;
let crash_point = null;
let crash_startTime = null;
let crash_crashed = false;

function crash_calcMultiplier() {
    const elapsed = (Date.now() - crash_startTime) / 1000;
    return 1.0 + Math.pow(elapsed, 1.3);
}

function crash_updateUI(m) {
    const el = document.getElementById("multiplier");
    el.innerText = m.toFixed(2) + "x";

    if (m < 1.5) el.className = "green";
    else if (m < 3.0) el.className = "yellow";
    else el.className = "red";

    el.style.transform = "scale(1.1)";
    setTimeout(() => el.style.transform = "scale(1.0)", 100);
}

async function crash_loadHistory() {
    const res = await fetch("/crash_history");
    const data = await res.json();
    document.getElementById("history").innerText =
        "履歴: " + data.history.join(" / ");
}

async function crash_start() {
    const bet = Number(document.getElementById("bet").value);

    const res = await fetch("/crash_start", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ bet })
    });

    const data = await res.json();

    if (data.error) {
        alert(data.error);
        return;
    }

    crash_point = data.crash_point;
    crash_startTime = Date.now();
    crash_crashed = false;

    document.getElementById("cashoutBtn").disabled = false;
    document.getElementById("startBtn").disabled = true;

    crash_interval = setInterval(() => {
        const m = crash_calcMultiplier();

        if (m >= crash_point) {
            clearInterval(crash_interval);
            crash_crashed = true;
            crash_crashUI();
            crash_saveHistory(crash_point);
            document.getElementById("cashoutBtn").disabled = true;
            document.getElementById("startBtn").disabled = false;
            return;
        }

        crash_updateUI(m);
    }, 100);
}

function crash_crashUI() {
    const el = document.getElementById("multiplier");
    el.innerText = "CRASH!";
    el.className = "red";
    el.style.transform = "scale(1.3)";
    setTimeout(() => el.style.transform = "scale(1.0)", 300);
}

async function crash_cashout() {
    if (crash_crashed) return;

    clearInterval(crash_interval);
    const m = crash_calcMultiplier();
    crash_updateUI(m);

    const res = await fetch("/crash_cashout", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ multiplier: m })
    });

    const data = await res.json();
    alert("逃げ成功！ +" + data.payout + " コイン");

    document.getElementById("cashoutBtn").disabled = true;
    document.getElementById("startBtn").disabled = false;
}

async function crash_saveHistory(point) {
    await fetch("/crash_save", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ crash_point: point })
    });

    crash_loadHistory();
}

document.getElementById("startBtn").onclick = crash_start;
document.getElementById("cashoutBtn").onclick = crash_cashout;

crash_loadHistory();
</script>

</body>
</html>
""")

@app.route("/crash_start", methods=["POST"])
@login_required
def crash_start():
    data = request.json
    bet = int(data["bet"])

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    if bet <= 0 or bet > coins:
        cur.close()
        put_conn(conn)
        return jsonify({"error": "ベット額が不正です"}), 400

    coins -= bet
    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()
    cur.close()
    put_conn(conn)

    session["crash_bet"] = bet
    session["crash_start_time"] = time.time()

    crash_point = generate_crash_point()

    return jsonify({
        "crash_point": crash_point,
        "coins": coins
    })

@app.route("/crash_cashout", methods=["POST"])
@login_required
def crash_cashout():
    data = request.json

    multiplier = float(str(data["multiplier"]).replace("x", ""))

    bet = session.get("crash_bet")
    payout = int(bet * multiplier)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE id=%s", (current_user.id,))
    coins = cur.fetchone()[0]

    coins += payout
    cur.execute("UPDATE users SET coins=%s WHERE id=%s", (coins, current_user.id))
    conn.commit()

    cur.close()
    put_conn(conn)

    session.pop("crash_bet", None)
    session.pop("crash_start_time", None)

    return jsonify({"payout": payout, "coins": coins})

@app.route("/crash_save", methods=["POST"])
@login_required
def crash_save():
    data = request.json
    crash_point = data["crash_point"]

    supabase.table("crash_history").insert({
        "crash_point": crash_point
    }).execute()

    return jsonify({"status": "ok"})


@app.route("/crash_history")
@login_required
def crash_history():
    res = supabase.table("crash_history").select("crash_point").order("id", desc=True).limit(10).execute()
    points = [row["crash_point"] for row in res.data]
    return jsonify({"history": points})

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
