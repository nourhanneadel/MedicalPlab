import os
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
import bcrypt
import jwt

DB_PATH_DEFAULT = "Data/db/merged.db"
CONFIG_PATH_DEFAULT = "Data/config/app_settings.json"
JWT_SECRET = os.getenv("JWT_SECRET", "medplab-jwt-production-secret-2026")
JWT_ALGORITHM = "HS256"

def get_app_settings(config_path: str = CONFIG_PATH_DEFAULT) -> Dict[str, Any]:
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"free_tier_question_limit": 30, "daily_llm_limit": 20}

def init_auth_tables(db_path: str = DB_PATH_DEFAULT):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        subscription_status TEXT DEFAULT 'free',
        questions_answered_count INTEGER DEFAULT 0
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_question_access (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        question_id INTEGER NOT NULL,
        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, source, question_id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_daily_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        usage_date TEXT NOT NULL,
        call_count INTEGER DEFAULT 0,
        UNIQUE(user_id, usage_date),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS access_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None

def create_user(email: str, password: str, db_path: str = DB_PATH_DEFAULT) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "A valid email address is required.", None
    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return False, "An account with this email already exists.", None

    hashed = hash_password(password)
    cursor.execute(
        "INSERT INTO users (email, password_hash, subscription_status, questions_answered_count) VALUES (?, ?, ?, ?)",
        (email, hashed, "free", 0)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    user = {
        "id": user_id,
        "email": email,
        "subscription_status": "free",
        "questions_answered_count": 0
    }
    return True, "Account created successfully.", user

def authenticate_user(email: str, password: str, db_path: str = DB_PATH_DEFAULT) -> Optional[Dict[str, Any]]:
    email = email.strip().lower()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password_hash, subscription_status, questions_answered_count FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    user_id, u_email, pwd_hash, sub_status, q_count = row
    if not verify_password(password, pwd_hash):
        return None

    return {
        "id": user_id,
        "email": u_email,
        "subscription_status": sub_status,
        "questions_answered_count": q_count
    }

def get_user_by_id(user_id: int, db_path: str = DB_PATH_DEFAULT) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, subscription_status, questions_answered_count, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "subscription_status": row[2],
        "questions_answered_count": row[3],
        "created_at": row[4]
    }

def get_distinct_questions_accessed_count(user_id: int, db_path: str = DB_PATH_DEFAULT) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT source || ':' || question_id) FROM user_question_access WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    count = row[0] if row else 0
    conn.close()
    return count

def record_question_access(user_id: int, source: str, question_ids: List[int], db_path: str = DB_PATH_DEFAULT):
    if not question_ids:
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for q_id in question_ids:
        cursor.execute(
            "INSERT OR IGNORE INTO user_question_access (user_id, source, question_id) VALUES (?, ?, ?)",
            (user_id, source, q_id)
        )
    conn.commit()
    conn.close()

def get_accessed_question_ids(user_id: int, source: str, db_path: str = DB_PATH_DEFAULT) -> List[int]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT question_id FROM user_question_access WHERE user_id = ? AND source = ?", (user_id, source))
    ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    return ids

def increment_questions_answered(user_id: int, db_path: str = DB_PATH_DEFAULT):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET questions_answered_count = questions_answered_count + 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def check_and_increment_daily_llm_limit(user_id: int, db_path: str = DB_PATH_DEFAULT, config_path: str = CONFIG_PATH_DEFAULT) -> Tuple[bool, int, int]:
    settings = get_app_settings(config_path)
    limit = int(settings.get("daily_llm_limit", 20))
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT call_count FROM user_daily_usage WHERE user_id = ? AND usage_date = ?", (user_id, today_str))
    row = cursor.fetchone()
    current_count = row[0] if row else 0

    if current_count >= limit:
        conn.close()
        return False, current_count, limit

    new_count = current_count + 1
    cursor.execute("""
    INSERT INTO user_daily_usage (user_id, usage_date, call_count)
    VALUES (?, ?, 1)
    ON CONFLICT(user_id, usage_date) DO UPDATE SET call_count = call_count + 1
    """, (user_id, today_str))
    conn.commit()
    conn.close()
    return True, new_count, limit

def create_access_request(user_id: int, email: str, db_path: str = DB_PATH_DEFAULT) -> Tuple[bool, str, Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, requested_at FROM access_requests WHERE user_id = ? AND status = 'pending'", (user_id,))
    pending = cursor.fetchone()
    if pending:
        conn.close()
        return False, "Access request already submitted and pending administrator approval.", {
            "id": pending[0],
            "status": pending[1],
            "requested_at": pending[2],
            "already_requested": True
        }

    cursor.execute("INSERT INTO access_requests (user_id, email, status) VALUES (?, ?, 'pending')", (user_id, email))
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return True, "Access request submitted successfully.", {
        "id": req_id,
        "status": "pending",
        "already_requested": False
    }

def get_user_access_request_status(user_id: int, db_path: str = DB_PATH_DEFAULT) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM access_requests WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "none"

def get_all_access_requests(db_path: str = DB_PATH_DEFAULT) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, email, requested_at, status FROM access_requests ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "email": r[2],
            "requested_at": r[3],
            "status": r[4]
        }
        for r in rows
    ]

def approve_access_request(request_id: int, db_path: str = DB_PATH_DEFAULT) -> Tuple[bool, str]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, status FROM access_requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, f"Access request #{request_id} not found."

    user_id, status = row
    cursor.execute("UPDATE access_requests SET status = 'approved' WHERE id = ?", (request_id,))
    cursor.execute("UPDATE users SET subscription_status = 'active' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True, f"Access request #{request_id} approved. User #{user_id} upgraded to active."
