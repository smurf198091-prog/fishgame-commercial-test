#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import secrets
import shutil
import sqlite3
import time
import urllib.request
import zipfile
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "19200"))
HOST = os.environ.get("HOST", "0.0.0.0")
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = Path(os.environ.get("DB_PATH", str(DATA_DIR / "fishgame.sqlite3")))
GAME_DIR = Path(os.environ.get("GAME_DIR", str(DATA_DIR / "game")))
APP_ENV = os.environ.get("APP_ENV", "commercial-test")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
SOURCE_COMMIT = "9984867e5b0a1dc48fa821da35886f007a0a4917"
GAME_SOURCE_ZIP = os.environ.get(
    "GAME_SOURCE_ZIP",
    f"https://github.com/nguyenhoanghai1605/GameBanCa_Fish/archive/{SOURCE_COMMIT}.zip",
)

if len(ADMIN_TOKEN) < 16:
    raise RuntimeError("ADMIN_TOKEN must be set to a strong secret of at least 16 characters")

DATA_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS: dict[str, int] = {}
RATE: dict[str, deque[float]] = defaultdict(deque)


def now_ms() -> int:
    return int(time.time() * 1000)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS players(player_id TEXT PRIMARY KEY, coin INTEGER DEFAULT 0, fires INTEGER DEFAULT 0, captures INTEGER DEFAULT 0, status TEXT DEFAULT 'active', created_at INTEGER, updated_at INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, type TEXT, player_id TEXT, payload TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)")
    defaults = {
        "starting_coin": "10000",
        "commercial_test_mode": "true",
        "payments_enabled": "false",
        "withdrawals_enabled": "false",
        "operator_note": "商业测试：仅娱乐币，不接入真钱充值/提现。",
        "source_commit": SOURCE_COMMIT,
    }
    for key, value in defaults.items():
        conn.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?,?,?)", (key, value, now_ms()))
    return conn


def ensure_game_assets() -> None:
    if (GAME_DIR / "index.html").exists():
        return
    tmp_zip = DATA_DIR / "game-source.zip"
    tmp_extract = DATA_DIR / "game-extract"
    if tmp_extract.exists():
        shutil.rmtree(tmp_extract)
    print(f"Downloading pinned game source: {GAME_SOURCE_ZIP}")
    urllib.request.urlretrieve(GAME_SOURCE_ZIP, tmp_zip)
    with zipfile.ZipFile(tmp_zip, "r") as archive:
        archive.extractall(tmp_extract)
    candidates = list(tmp_extract.glob("**/index.html"))
    if not candidates:
        raise RuntimeError("No index.html found in downloaded game source")
    if GAME_DIR.exists():
        shutil.rmtree(GAME_DIR)
    shutil.copytree(candidates[0].parent, GAME_DIR)
    patch_game_files()


def patch_game_files() -> None:
    index = GAME_DIR / "index.html"
    if index.exists():
        original = index.read_text(encoding="utf-8", errors="ignore")
        if "fitGame" not in original:
            patched = original.replace(
                '<meta name="apple-mobile-web-app-status-bar-style" content="black" />',
                '<meta name="apple-mobile-web-app-status-bar-style" content="black" />\n<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />',
            )
            patched = patched.replace("#outer{height:100%; overflow:hidden; position:relative; width:100%;}", "#outer{position:fixed; inset:0; overflow:hidden; width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:#000;}")
            patched = patched.replace("#middle{position:absolute; top:50%;}", "#middle{position:relative; width:980px; height:545px; transform-origin:center center;}")
            patched = patched.replace("#middle[id]{display:table-cell; vertical-align:middle; position:static;}", "#middle[id]{display:block; position:relative;}")
            patched = patched.replace('<div id="container" style="position:relative;width:980px;height:545px;top:-50%;margin:0 auto;"></div>', '<div id="container" style="position:relative;width:980px;height:545px;margin:0 auto;overflow:hidden;"></div>')
            patched = patched.replace("</head>", "<script>function fitGame(){var s=Math.min(window.innerWidth/980,window.innerHeight/545);var m=document.getElementById('middle');if(m)m.style.transform='scale('+s+')';}window.addEventListener('resize',fitGame);window.addEventListener('load',fitGame);</script>\n</head>")
            index.write_text(patched, encoding="utf-8")

    player = GAME_DIR / "src" / "views" / "Player.js"
    if player.exists():
        text = player.read_text(encoding="utf-8", errors="ignore")
        if "backendEvent" not in text:
            text = text.replace(
                'var ns = Q.use("fish"), game = ns.game;',
                'var ns = Q.use("fish"), game = ns.game;\nfunction backendEvent(type,payload){try{payload=payload||{};payload.type=type;payload.ts=Date.now();var body=JSON.stringify(payload);var send=function(t){return fetch("/api/event",{method:"POST",headers:{"Content-Type":"application/json","X-Game-Session":t},body:body,keepalive:true}).catch(function(){});};fetch("/api/session").then(function(r){return r.json()}).then(function(s){if(s&&s.token)send(s.token)}).catch(function(){});}catch(e){}}',
            )
            text = text.replace('this.updateCoin(-power, true);', 'this.updateCoin(-power, true);\n\tbackendEvent("fire", {player_id:this.id || "local-player", power:power, coin:this.coin});')
            text = text.replace('this.numCapturedFishes++;', 'this.numCapturedFishes++;\n\tbackendEvent("capture", {player_id:this.id || "local-player", fish_id:fish.id, coin_value:fish.coin, coin:this.coin, captured:this.numCapturedFishes});')
            text = text.replace('this.coinNum.setValue(this.coin);', 'this.coinNum.setValue(this.coin);\n\tbackendEvent("coin_update", {player_id:this.id || "local-player", coin:this.coin});')
            player.write_text(text, encoding="utf-8")


def jdump(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")


ADMIN_HTML = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>捕鱼商业测试后台</title><style>body{margin:0;background:#07111f;color:#eaf6ff;font-family:system-ui,-apple-system,Segoe UI,sans-serif}.wrap{max-width:1240px;margin:0 auto;padding:28px 18px}.muted{color:#9db9d3}.card{background:#0b1d34;border:1px solid #24476f;border-radius:18px;padding:18px;margin:14px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.num{font-size:30px;font-weight:900;color:#ffd66b}button,a.btn,input{border:0;border-radius:12px;padding:10px 14px;font-weight:800}button,a.btn{background:#37a2ff;color:#00182d;text-decoration:none;cursor:pointer}.danger{background:#832338!important;color:#fff!important}input{background:#061225;color:#eaf6ff;border:1px solid #315781;min-width:320px}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #193451;padding:9px;text-align:left;font-size:13px}pre{white-space:pre-wrap;max-height:400px;overflow:auto;background:#030812;padding:14px;border-radius:14px;border:1px solid #193451}.ok{color:#72ffb6}.bar{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}</style></head><body><div class="wrap"><h1>🎣 捕鱼商业测试后台</h1><p class="muted">海外商业测试版：H5 游戏 + SQLite 后台 + 娱乐币运营数据。默认禁用真钱充值/提现。</p><div id="login" class="card"><h2>后台登录</h2><input id="pwd" type="password" placeholder="ADMIN_TOKEN"><button onclick="loginNow()">登录</button></div><div id="app" style="display:none"><div class="bar"><a class="btn" href="/game/" target="_blank">打开游戏端</a><button onclick="load()">刷新</button><button class="danger" onclick="resetAll()">清空测试数据</button></div><div class="grid"><div class="card"><div class="muted">状态</div><div class="num ok" id="status">--</div></div><div class="card"><div class="muted">玩家数</div><div class="num" id="players">0</div></div><div class="card"><div class="muted">发炮</div><div class="num" id="fires">0</div></div><div class="card"><div class="muted">捕获</div><div class="num" id="captures">0</div></div><div class="card"><div class="muted">事件</div><div class="num" id="eventsCount">0</div></div></div><div class="card"><h2>玩家账户</h2><div id="playerTable"></div></div><div class="card"><h2>最近事件</h2><pre id="events">loading...</pre></div></div></div><script>let token=localStorage.getItem('adminToken')||'';function headers(){return {'X-Admin-Token':token,'Content-Type':'application/json'}}function loginNow(){token=pwd.value;localStorage.setItem('adminToken',token);login.style.display='none';app.style.display='block';load()}async function api(p,o={}){o.headers=Object.assign(headers(),o.headers||{});const r=await fetch(p,o);if(r.status===401){localStorage.removeItem('adminToken');alert('Token 不对');location.reload()}return await r.json()}if(token){login.style.display='none';app.style.display='block';load()}async function load(){const s=await api('/api/admin/state');status.textContent=s.status;players.textContent=s.summary.players;fires.textContent=s.summary.fires;captures.textContent=s.summary.captures;eventsCount.textContent=s.summary.events;playerTable.innerHTML='<table><tr><th>player_id</th><th>coin</th><th>fires</th><th>captures</th><th>updated</th></tr>'+s.players.map(p=>`<tr><td>${p.player_id}</td><td>${p.coin}</td><td>${p.fires}</td><td>${p.captures}</td><td>${new Date(p.updated_at).toLocaleString()}</td></tr>`).join('')+'</table>';events.textContent=JSON.stringify(s.events,null,2)}async function resetAll(){if(confirm('清空测试数据？')){await api('/api/admin/reset',{method:'POST'});load()}}setInterval(()=>{if(app.style.display!=='none')load()},5000)</script></body></html>'''


def client_ip(handler: BaseHTTPRequestHandler) -> str:
    forwarded = handler.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or handler.client_address[0]


def rate_ok(ip: str, limit: int = 120, window: int = 60) -> bool:
    q = RATE[ip]
    now = time.time()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def admin_ok(handler: BaseHTTPRequestHandler) -> bool:
    return secrets.compare_digest(handler.headers.get("X-Admin-Token", ""), ADMIN_TOKEN)


def session_ok(handler: BaseHTTPRequestHandler) -> bool:
    token = handler.headers.get("X-Game-Session", "")
    expires = SESSIONS.get(token, 0)
    return bool(token and expires > now_ms())


class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj, status=200, extra_headers=None):
        body = jdump(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/":
            self.send_response(302)
            self.send_header("Location", "/admin")
            self.end_headers()
            return
        if p == "/admin":
            self.send_html(ADMIN_HTML)
            return
        if p == "/api/health":
            self.send_json({"status": "ok", "env": APP_ENV, "game_ready": (GAME_DIR / "index.html").exists(), "payments_enabled": False, "source_commit": SOURCE_COMMIT, "time_ms": now_ms()})
            return
        if p == "/api/session":
            ip = client_ip(self)
            if not rate_ok("session:" + ip, 30, 60):
                self.send_json({"error": "rate_limited"}, 429)
                return
            token = secrets.token_urlsafe(24)
            SESSIONS[token] = now_ms() + 2 * 60 * 60 * 1000
            self.send_json({"token": token, "expires_in": 7200})
            return
        if p == "/api/admin/state":
            if not admin_ok(self):
                self.send_json({"error": "unauthorized"}, 401)
                return
            with connect() as c:
                players = [dict(r) for r in c.execute("SELECT * FROM players ORDER BY updated_at DESC LIMIT 200")]
                events = [dict(r) for r in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 80")]
                for e in events:
                    try:
                        e["payload"] = json.loads(e["payload"])
                    except Exception:
                        pass
                summary = {
                    "players": len(players),
                    "fires": c.execute("SELECT COUNT(*) c FROM events WHERE type='fire'").fetchone()["c"],
                    "captures": c.execute("SELECT COUNT(*) c FROM events WHERE type='capture'").fetchone()["c"],
                    "events": c.execute("SELECT COUNT(*) c FROM events").fetchone()["c"],
                }
            self.send_json({"status": "ok", "summary": summary, "players": players, "events": events})
            return
        if p.startswith("/game"):
            rel = unquote(p[len("/game"):].lstrip("/") or "index.html").replace("\\", "/")
            target = (GAME_DIR / rel).resolve()
            if not str(target).startswith(str(GAME_DIR.resolve())):
                self.send_error(403)
                return
            self.serve_file(target)
            return
        self.send_error(404)

    def do_POST(self):
        p = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            data = {}
        if p == "/api/event":
            ip = client_ip(self)
            if not session_ok(self) or not rate_ok("event:" + ip, 120, 60):
                self.send_json({"error": "unauthorized_or_rate_limited"}, 401)
                return
            typ = str(data.get("type") or "unknown")[:40]
            player = str(data.get("player_id") or "local-player")[:80]
            ts = int(data.get("ts") or now_ms())
            coin = int(data.get("coin") or 0)
            with connect() as c:
                c.execute("INSERT INTO events(ts,type,player_id,payload) VALUES(?,?,?,?)", (ts, typ, player, json.dumps(data, ensure_ascii=False)[:4000]))
                if c.execute("SELECT 1 FROM players WHERE player_id=?", (player,)).fetchone() is None:
                    c.execute("INSERT INTO players(player_id,coin,fires,captures,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (player, coin, 0, 0, "active", ts, ts))
                if typ == "fire":
                    c.execute("UPDATE players SET coin=?,fires=fires+1,updated_at=? WHERE player_id=?", (coin, ts, player))
                elif typ == "capture":
                    c.execute("UPDATE players SET coin=?,captures=captures+1,updated_at=? WHERE player_id=?", (coin, ts, player))
                elif typ == "coin_update":
                    c.execute("UPDATE players SET coin=?,updated_at=? WHERE player_id=?", (coin, ts, player))
            self.send_json({"ok": True})
            return
        if p == "/api/admin/reset":
            if not admin_ok(self):
                self.send_json({"error": "unauthorized"}, 401)
                return
            with connect() as c:
                c.execute("DELETE FROM events")
                c.execute("DELETE FROM players")
            self.send_json({"ok": True})
            return
        self.send_error(404)


def main():
    with connect():
        pass
    ensure_game_assets()
    print(f"Game : http://127.0.0.1:{PORT}/game/")
    print(f"Admin: http://127.0.0.1:{PORT}/admin")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
