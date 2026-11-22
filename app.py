import os, time, secrets, sqlite3, re
from collections import defaultdict, deque
from functools import wraps
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "")
ESP32_URL = os.getenv("ESP32_URL", "").rstrip("/")
ESP32_API_KEY = os.getenv("ESP32_API_KEY", "")
missing = [k for k,v in {"FLASK_SECRET_KEY":SECRET_KEY,"ESP32_URL":ESP32_URL,"ESP32_API_KEY":ESP32_API_KEY}.items() if not v or "CHANGE_ME" in v]
if missing: raise SystemExit("กรุณาตั้งค่าใน .env ให้ครบ: " + ", ".join(missing))

DB_PATH = os.path.join(BASE_DIR, "smartfarm_users.db")
def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn
with db() as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL COLLATE NOCASE UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

app=Flask(__name__, static_folder=None)
app.secret_key=SECRET_KEY
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=False, PERMANENT_SESSION_LIFETIME=86400,
                  MAX_CONTENT_LENGTH=4096)
login_attempts=defaultdict(deque)
ALLOWED_API={"/api/status":{"GET"},"/api/pump":{"POST"},"/api/threshold":{"POST"},"/api/mode":{"POST"}}

def csrf_ok():
    token=request.headers.get("X-CSRF-Token","")
    return bool(token and session.get("csrf_token") and secrets.compare_digest(token,session["csrf_token"]))
def login_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if not session.get("authenticated"): return jsonify(error="กรุณาเข้าสู่ระบบ"),401
        return fn(*a,**kw)
    return wrapped
def rate_limited(key, limit=8):
    now=time.time(); q=login_attempts[key]
    while q and now-q[0]>300: q.popleft()
    if len(q)>=limit: return True
    q.append(now); return False
@app.after_request
def security_headers(response):
    response.headers["Cache-Control"]="no-store"
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="same-origin"
    return response
@app.get("/")
def index(): return send_from_directory(BASE_DIR,"index.html")
@app.get("/auth/me")
def auth_me():
    if session.get("authenticated"): return jsonify(authenticated=True,csrf_token=session["csrf_token"],username=session.get("username"))
    return jsonify(authenticated=False)
@app.post("/auth/register")
def auth_register():
    key="register:"+str(request.remote_addr or "unknown")
    if rate_limited(key,8): return jsonify(error="สมัครหลายครั้งเกินไป กรุณารอ 5 นาที"),429
    data=request.get_json(silent=True) or {}
    username=str(data.get("username","")).strip()
    password=str(data.get("password",""))
    if not re.fullmatch(r"[A-Za-z0-9ก-๙_.-]{3,32}",username):
        return jsonify(error="ชื่อผู้ใช้ต้องมี 3–32 ตัวอักษร ใช้ภาษาไทย อังกฤษ ตัวเลข _ . - ได้"),400
    if len(password)<8: return jsonify(error="รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร"),400
    try:
        with db() as conn:
            cur=conn.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",(username,generate_password_hash(password)))
            user_id=cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify(error="ชื่อผู้ใช้นี้ถูกใช้แล้ว กรุณาเลือกชื่ออื่น"),409
    session.clear(); session["authenticated"]=True; session["user_id"]=user_id
    session["username"]=username; session["csrf_token"]=secrets.token_urlsafe(32); session.permanent=True
    return jsonify(ok=True,csrf_token=session["csrf_token"],username=username)
@app.post("/auth/login")
def auth_login():
    key="login:"+str(request.remote_addr or "unknown")
    if rate_limited(key,8): return jsonify(error="ลองเข้าสู่ระบบหลายครั้งเกินไป กรุณารอ 5 นาที"),429
    data=request.get_json(silent=True) or {}
    username=str(data.get("username","")).strip(); password=str(data.get("password",""))
    with db() as conn: user=conn.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
    if not user or not check_password_hash(user["password_hash"],password):
        return jsonify(error="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"),401
    session.clear(); session["authenticated"]=True; session["user_id"]=user["id"]
    session["username"]=user["username"]; session["csrf_token"]=secrets.token_urlsafe(32); session.permanent=True
    return jsonify(ok=True,csrf_token=session["csrf_token"],username=user["username"])
@app.post("/auth/logout")
@login_required
def auth_logout():
    if not csrf_ok(): return jsonify(error="CSRF token ไม่ถูกต้อง"),403
    session.clear(); return jsonify(ok=True)
@app.route("/api/<path:subpath>",methods=["GET","POST"])
@login_required
def proxy_api(subpath):
    path="/api/"+subpath; method=request.method
    if path not in ALLOWED_API or method not in ALLOWED_API[path]: return jsonify(error="ไม่อนุญาต API นี้"),404
    if not csrf_ok(): return jsonify(error="CSRF token ไม่ถูกต้อง"),403
    headers={"X-API-Key":ESP32_API_KEY}; body=request.get_data() if method=="POST" else None
    if body: headers["Content-Type"]="application/json"
    try:
        upstream=requests.request(method,ESP32_URL+path,headers=headers,data=body,timeout=3,allow_redirects=False)
        return (upstream.content,upstream.status_code,{"Content-Type":upstream.headers.get("Content-Type","application/json")})
    except requests.RequestException: return jsonify(error="ติดต่อ ESP32 ไม่สำเร็จ ตรวจสอบ IP และ Wi-Fi"),502
if __name__=="__main__":
    app.run(host="127.0.0.1",port=8000,debug=False)
