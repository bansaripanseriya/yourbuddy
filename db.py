"""
Supabase database for user accounts (sign up / login) and profiles.
Identifier is email or phone number; stored normalized for uniqueness.
Set SUPABASE_URL and SUPABASE_KEY in .env. Run supabase_schema.sql in Supabase SQL Editor once.
"""
import base64
import hashlib
import re
from decouple import config
from supabase import create_client, Client

# Supabase (.env: SUPABASE_URL, SUPABASE_KEY)
SUPABASE_URL = config("SUPABASE_URL", default="")
SUPABASE_KEY = config("SUPABASE_KEY", default="")
PASSWORD_SALT = config("PASSWORD_SALT", default="yourbuddy_salt").encode("utf-8")

# Simple email pattern
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _is_valid_email(s: str) -> bool:
    return bool(s and _EMAIL_RE.match(s.strip()))


def _normalize_identifier(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if "@" in s:
        return s.lower()
    return s


def _validate_email_or_phone(s: str) -> tuple[bool, str]:
    s = (s or "").strip()
    if not s:
        return False, "Email is required."
    if "@" in s:
        if not _is_valid_email(s):
            return False, "Please enter a valid email address."
        return True, ""
    return False, "Please use your email address. Phone login is temporarily disabled."


def _hash_password(password: str) -> str:
    return hashlib.sha256(PASSWORD_SALT + password.encode("utf-8")).hexdigest()


def _get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db() -> None:
    """No-op: tables are created in Supabase via supabase_schema.sql. Kept for API compatibility."""
    pass


def normalize_identifier(identifier: str) -> str:
    return _normalize_identifier(identifier)


def validate_email_or_phone(s: str) -> tuple[bool, str]:
    return _validate_email_or_phone(s)


def save_otp(identifier: str, code: str, valid_minutes: int = 10) -> None:
    from datetime import datetime, timezone, timedelta
    key = _normalize_identifier(identifier)
    if not key:
        return
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=valid_minutes)).isoformat()
    client = _get_client()
    client.table("otp").upsert(
        {"identifier": key, "code": code, "expires_at": expires_at},
        on_conflict="identifier",
    ).execute()


def verify_and_consume_otp(identifier: str, code: str) -> bool:
    from datetime import datetime, timezone
    key = _normalize_identifier(identifier or "")
    if not key or not (code or "").strip():
        return False
    code_clean = (code or "").strip()
    client = _get_client()
    r = client.table("otp").select("code, expires_at").eq("identifier", key).execute()
    if not r.data or len(r.data) == 0:
        return False
    row = r.data[0]
    stored_code = row["code"]
    expires_at = row["expires_at"]
    if stored_code != code_clean:
        return False
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except Exception:
        expiry = datetime.now(timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        client.table("otp").delete().eq("identifier", key).execute()
        return False
    client.table("otp").delete().eq("identifier", key).execute()
    return True


def user_exists(identifier: str) -> bool:
    key = _normalize_identifier(identifier)
    if not key:
        return False
    client = _get_client()
    r = client.table("users").select("username").eq("username", key).execute()
    return bool(r.data and len(r.data) > 0)


def create_user(identifier: str, password: str) -> tuple[bool, str]:
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
        client = _get_client()
        client.table("users").insert({"username": key, "password_hash": password_hash}).execute()
        return True, "Account created. You can log in now."
    except Exception as e:
        err_msg = str(e).lower()
        if "unique" in err_msg or "duplicate" in err_msg or "already" in err_msg:
            return False, "This email is already registered."
        return False, str(e)


def verify_user(identifier: str, password: str) -> bool:
    key = _normalize_identifier(identifier or "")
    if not key or not password:
        return False
    password_hash = _hash_password(password)
    client = _get_client()
    r = client.table("users").select("username").eq("username", key).eq("password_hash", password_hash).execute()
    return bool(r.data and len(r.data) > 0)


def update_password(identifier: str, new_password: str) -> tuple[bool, str]:
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
    client = _get_client()
    r = client.table("users").update({"password_hash": password_hash}).eq("username", key).execute()
    if not r.data or len(r.data) == 0:
        return False, "No account found with that email."
    return True, "Password updated. You can log in with your new password."


def get_user_profile(identifier: str) -> dict | None:
    key = _normalize_identifier(identifier or "")
    if not key:
        return None
    client = _get_client()
    r = client.table("users").select("username, created_at").eq("username", key).execute()
    if not r.data or len(r.data) == 0:
        return None
    u = r.data[0]
    created_at = u.get("created_at") or ""
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    profile = {
        "email": u["username"],
        "created_at": created_at,
        "name": "",
        "age": None,
        "phone": "",
        "blood_group": "",
        "profile_photo": None,
        "gender": "",
        "bio": "",
        "date_of_birth": "",
    }
    pr = client.table("user_profiles").select("*").eq("username", key).execute()
    if pr.data and len(pr.data) > 0:
        p = pr.data[0]
        profile["name"] = p.get("name") or ""
        profile["age"] = p.get("age")
        profile["phone"] = p.get("phone") or ""
        profile["blood_group"] = p.get("blood_group") or ""
        raw_photo = p.get("profile_photo")
        if raw_photo:
            try:
                profile["profile_photo"] = base64.b64decode(raw_photo)
            except Exception:
                profile["profile_photo"] = None
        profile["gender"] = p.get("gender") or ""
        profile["bio"] = p.get("bio") or ""
        profile["date_of_birth"] = p.get("date_of_birth") or ""
    return profile


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
    if bio is not None and len(bio) > 500:
        return False, "Bio must be 500 characters or less."
    key = _normalize_identifier(identifier or "")
    if not key:
        return False, "User not found."
    client = _get_client()
    r = client.table("user_profiles").select("name, age, phone, blood_group, profile_photo, gender, bio, date_of_birth").eq("username", key).execute()
    existing = r.data[0] if r.data and len(r.data) > 0 else None
    if existing:
        n = name if name is not None else (existing.get("name") or "")
        a = age if age is not None else existing.get("age")
        ph = phone if phone is not None else (existing.get("phone") or "")
        bg = blood_group if blood_group is not None else (existing.get("blood_group") or "")
        pic_b64 = base64.b64encode(profile_photo).decode("utf-8") if profile_photo is not None else (existing.get("profile_photo") or "")
        g = gender if gender is not None else (existing.get("gender") or "")
        b = bio if bio is not None else (existing.get("bio") or "")
        dob = date_of_birth if date_of_birth is not None else (existing.get("date_of_birth") or "")
        client.table("user_profiles").update({
            "name": n, "age": a, "phone": ph, "blood_group": bg,
            "profile_photo": pic_b64 or None, "gender": g, "bio": b, "date_of_birth": dob,
        }).eq("username", key).execute()
    else:
        pic_b64 = base64.b64encode(profile_photo).decode("utf-8") if profile_photo else ""
        client.table("user_profiles").insert({
            "username": key,
            "name": name or "",
            "age": age,
            "phone": phone or "",
            "blood_group": blood_group or "",
            "profile_photo": pic_b64 or None,
            "gender": gender or "",
            "bio": bio or "",
            "date_of_birth": date_of_birth or "",
        }).execute()
    return True, "Profile updated."
