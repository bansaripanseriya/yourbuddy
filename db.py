"""
SQLite database for user accounts (sign up / login).
Identifier is email or phone number; stored normalized for uniqueness.
"""
import hashlib
import re
import sqlite3
from pathlib import Path
from decouple import config

# Database file in project directory
DB_PATH = Path(__file__).resolve().parent / "yourbuddy.db"
# Salt for password hashing (.env: PASSWORD_SALT)
PASSWORD_SALT = config("PASSWORD_SALT").encode("utf-8")

# Simple email pattern: something@something.something
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _is_valid_email(s: str) -> bool:
    return bool(s and _EMAIL_RE.match(s.strip()))


# --- Phone (commented out until TWILIO_ACCOUNT_SID etc. are set) ---
# def _normalize_phone(s: str) -> str:
#     """Extract digits only; allow leading + for international."""
#     s = (s or "").strip()
#     digits = "".join(c for c in s if c.isdigit())
#     return digits
#
# def _is_valid_phone(s: str) -> bool:
#     digits = _normalize_phone(s)
#     return len(digits) >= 10


def _normalize_identifier(s: str) -> str:
    """
    Normalize email for storage and lookup.
    (Phone support commented out until Twilio is configured.)
    """
    s = (s or "").strip()
    if not s:
        return ""
    if "@" in s:
        return s.lower()
    # return _normalize_phone(s)  # phone disabled for now
    return s  # fallback: leave as-is if not email (will fail validation)


def _validate_email_or_phone(s: str) -> tuple[bool, str]:
    """Return (valid, error_message). Email only for now; phone commented out."""
    s = (s or "").strip()
    if not s:
        return False, "Email is required."
    if "@" in s:
        if not _is_valid_email(s):
            return False, "Please enter a valid email address."
        return True, ""
    # Phone temporarily disabled (no Twilio)
    return False, "Please use your email address. Phone login is temporarily disabled."
    # if not _is_valid_phone(s):
    #     return False, "Please enter a valid phone number (at least 10 digits)."
    # return True, ""


def _hash_password(password: str) -> str:
    """Return SHA-256 hash of salt + password."""
    return hashlib.sha256(PASSWORD_SALT + password.encode("utf-8")).hexdigest()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create users and otp tables if they do not exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otp (
                identifier TEXT NOT NULL PRIMARY KEY,
                code TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                username TEXT NOT NULL PRIMARY KEY,
                name TEXT,
                age INTEGER,
                phone TEXT,
                blood_group TEXT,
                profile_photo BLOB,
                gender TEXT,
                bio TEXT,
                date_of_birth TEXT
            )
        """)
        # Add new columns if table already existed without them
        for col in ("gender", "bio", "date_of_birth"):
            try:
                conn.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass
        conn.commit()


def normalize_identifier(identifier: str) -> str:
    """Public wrapper for use by api/UI. Normalize email or phone for storage."""
    return _normalize_identifier(identifier)


def validate_email_or_phone(s: str) -> tuple[bool, str]:
    """Return (valid, error_message). Public for api."""
    return _validate_email_or_phone(s)


def save_otp(identifier: str, code: str, valid_minutes: int = 10) -> None:
    """Store OTP for identifier. Replaces any existing OTP for that identifier."""
    init_db()
    key = _normalize_identifier(identifier)
    if not key:
        return
    from datetime import datetime, timedelta
    expires_at = (datetime.utcnow() + timedelta(minutes=valid_minutes)).strftime("%Y-%m-%dT%H:%M:%S")
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO otp (identifier, code, expires_at) VALUES (?, ?, ?)",
            (key, code, expires_at),
        )
        conn.commit()


def verify_and_consume_otp(identifier: str, code: str) -> bool:
    """Return True if code matches and is not expired; then delete the OTP."""
    init_db()
    key = _normalize_identifier(identifier or "")
    if not key or not (code or "").strip():
        return False
    code_clean = (code or "").strip()
    from datetime import datetime
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT code, expires_at FROM otp WHERE identifier = ?",
            (key,),
        ).fetchone()
        if not row:
            return False
        stored_code, expires_at = row[0], row[1]
        if stored_code != code_clean:
            return False
        try:
            expiry = datetime.fromisoformat(expires_at)
        except Exception:
            expiry = datetime.utcnow()
        if expiry <= datetime.utcnow():
            conn.execute("DELETE FROM otp WHERE identifier = ?", (key,))
            conn.commit()
            return False
        conn.execute("DELETE FROM otp WHERE identifier = ?", (key,))
        conn.commit()
    return True


def user_exists(identifier: str) -> bool:
    """Return True if this email or phone is already registered."""
    init_db()
    key = _normalize_identifier(identifier)
    if not key:
        return False
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (key,),
        ).fetchone()
    return row is not None


def create_user(identifier: str, password: str) -> tuple[bool, str]:
    """
    Register a new user with email or phone. Returns (success, message).
    Message is error description on failure.
    """
    init_db()
    identifier = (identifier or "").strip()
    ok, err = _validate_email_or_phone(identifier)
    if not ok:
        return False, err
    if not password:
        return False, "Password is required."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    key = _normalize_identifier(identifier)
    if user_exists(key):
        return False, "This email is already registered."

    password_hash = _hash_password(password)
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (key, password_hash),
            )
            conn.commit()
        return True, "Account created. You can log in now."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    except Exception as e:
        return False, str(e)


def verify_user(identifier: str, password: str) -> bool:
    """Return True if email/phone and password match a user in the database."""
    init_db()
    key = _normalize_identifier(identifier or "")
    if not key or not password:
        return False
    password_hash = _hash_password(password)
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE username = ? AND password_hash = ?",
            (key, password_hash),
        ).fetchone()
    return row is not None


def update_password(identifier: str, new_password: str) -> tuple[bool, str]:
    """
    Set a new password for the given email or phone. Returns (success, message).
    Used for forgot-password flow.
    """
    init_db()
    ok, err = _validate_email_or_phone(identifier or "")
    if not ok:
        return False, err
    key = _normalize_identifier(identifier or "")
    if not key:
        return False, "Email is required."
    if not new_password:
        return False, "Password is required."
    if len(new_password) < 4:
        return False, "Password must be at least 4 characters."
    if not user_exists(key):
        return False, "No account found with that email."

    password_hash = _hash_password(new_password)
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (password_hash, key),
        )
        conn.commit()
    if cur.rowcount == 0:
        return False, "No account found with that email."
    return True, "Password updated. You can log in with your new password."


def get_user_profile(identifier: str) -> dict | None:
    """Return profile dict (email, created_at, name, age, phone, blood_group, profile_photo) for the user, or None if not found."""
    init_db()
    key = _normalize_identifier(identifier or "")
    if not key:
        return None
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT u.username, u.created_at, p.name, p.age, p.phone, p.blood_group, p.profile_photo, p.gender, p.bio, p.date_of_birth "
            "FROM users u LEFT JOIN user_profiles p ON u.username = p.username WHERE u.username = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    return {
        "email": row[0],
        "created_at": row[1],
        "name": row[2] or "",
        "age": row[3],
        "phone": row[4] or "",
        "blood_group": row[5] or "",
        "profile_photo": row[6],
        "gender": row[7] or "",
        "bio": row[8] or "",
        "date_of_birth": row[9] or "",
    }


def update_user_profile(
    identifier: str,
    name: str | None = None,
    age: int | None = None,
    phone: str | None = None,
    blood_group: str | None = None,
    profile_photo: bytes | None = None,
    gender: str | None = None,
    bio: str | None = None,
    date_of_birth: str | None = None,
) -> tuple[bool, str]:
    """Update or create user profile. Returns (success, message). Pass None for fields to leave unchanged. Bio max 500 chars."""
    if bio is not None and len(bio) > 500:
        return False, "Bio must be 500 characters or less."
    init_db()
    key = _normalize_identifier(identifier or "")
    if not key:
        return False, "User not found."
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT name, age, phone, blood_group, profile_photo, gender, bio, date_of_birth FROM user_profiles WHERE username = ?", (key,)
        ).fetchone()
        if existing:
            n = name if name is not None else existing[0]
            a = age if age is not None else existing[1]
            ph = phone if phone is not None else existing[2]
            bg = blood_group if blood_group is not None else existing[3]
            pic = profile_photo if profile_photo is not None else existing[4]
            g = gender if gender is not None else (existing[5] if len(existing) > 5 else "")
            b = bio if bio is not None else (existing[6] if len(existing) > 6 else "")
            dob = date_of_birth if date_of_birth is not None else (existing[7] if len(existing) > 7 else "")
            conn.execute(
                "UPDATE user_profiles SET name=?, age=?, phone=?, blood_group=?, profile_photo=?, gender=?, bio=?, date_of_birth=? WHERE username=?",
                (n, a, ph, bg, pic, g, b, dob, key),
            )
        else:
            conn.execute(
                "INSERT INTO user_profiles (username, name, age, phone, blood_group, profile_photo, gender, bio, date_of_birth) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (key, (name or ""), age, (phone or ""), (blood_group or ""), profile_photo, (gender or ""), (bio or ""), (date_of_birth or "")),
            )
        conn.commit()
    return True, "Profile updated."
