"""
Backend/API: report generation, PDF build, report file read, and user auth (SQLite).
"""
import io
import os
import random

from report_utils import REPORT_PATH, generate_and_save_report

from database import (
    create_user as db_create_user,
    get_user_profile as db_get_user_profile,
    normalize_identifier as db_normalize_identifier,
    update_user_profile as db_update_user_profile,
    save_otp as db_save_otp,
    user_exists as db_user_exists,
    update_password as db_update_password,
    validate_email_or_phone as db_validate_email_or_phone,
    verify_and_consume_otp as db_verify_and_consume_otp,
    verify_user as db_verify_user,
)
from otp_sender import _is_email, send_contact_email, send_otp_email, send_otp_sms

__all__ = [
    "REPORT_PATH",
    "generate_and_save_report",
    "get_report_content",
    "build_pdf_bytes",
    "validate_login",
    "create_user",
    "user_exists",
    "update_password",
    "get_user_profile",
    "update_user_profile",
    "send_verification_code",
    "verify_otp_and_reset_password",
    "normalize_identifier",
    "send_contact_email",
]


def get_user_profile(identifier: str) -> dict | None:
    """Return profile dict (email, created_at, name, age, phone, blood_group, profile_photo) for the user, or None."""
    return db_get_user_profile(identifier)


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
    """Update user profile. Returns (success, message). Bio max 500 characters."""
    return db_update_user_profile(
        identifier, name=name, age=age, phone=phone, blood_group=blood_group,
        profile_photo=profile_photo, gender=gender, bio=bio, date_of_birth=date_of_birth,
    )


def validate_login(username: str, password: str) -> bool:
    """Return True if credentials match a user in the database."""
    return db_verify_user(username, password)


def create_user(username: str, password: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    return db_create_user(username, password)


def user_exists(username: str) -> bool:
    """Return True if username is already registered."""
    return db_user_exists(username)


def update_password(username: str, new_password: str) -> tuple[bool, str]:
    """Set a new password for the given username (forgot password). Returns (success, message)."""
    return db_update_password(username, new_password)


def normalize_identifier(identifier: str) -> str:
    """Normalize email or phone for storage/lookup."""
    return db_normalize_identifier(identifier)


def send_verification_code(identifier: str) -> tuple[bool, str]:
    """
    Send a 4-digit OTP to the given email or phone. Returns (success, message).
    User must already be registered.
    """
    ok, err = db_validate_email_or_phone(identifier or "")
    if not ok:
        return False, err
    key = db_normalize_identifier(identifier or "")
    if not db_user_exists(key):
        return False, "No account found with that email."
    code = "".join(str(random.randint(0, 9)) for _ in range(4))
    db_save_otp(identifier, code, valid_minutes=10)
    if _is_email(identifier or ""):
        return send_otp_email((identifier or "").strip(), code)
    # Phone OTP disabled until TWILIO_ACCOUNT_SID is set
    return False, "Please use your email address. Phone is temporarily not supported."
    # phone = key if key.startswith("+") else key
    # return send_otp_sms(phone, code)


def verify_otp_and_reset_password(identifier: str, otp: str, new_password: str) -> tuple[bool, str]:
    """
    Verify 4-digit OTP and set new password. Returns (success, message).
    """
    ok, err = db_validate_email_or_phone(identifier or "")
    if not ok:
        return False, err
    otp_clean = (otp or "").strip()
    if len(otp_clean) != 4 or not otp_clean.isdigit():
        return False, "Please enter a valid 4-digit code."
    if not new_password:
        return False, "Password is required."
    if len(new_password) < 4:
        return False, "Password must be at least 4 characters."
    if not db_verify_and_consume_otp(identifier, otp_clean):
        return False, "Invalid or expired code. Please request a new one."
    return db_update_password(identifier, new_password)


def get_report_content(report_path: str = REPORT_PATH) -> str | None:
    """Read report file content. Returns None if file does not exist."""
    if not os.path.isfile(report_path):
        return None
    with open(report_path, "r", encoding="utf-8") as f:
        return f.read()


def build_pdf_bytes(text: str, image_bytes: bytes | None = None) -> bytes | None:
    """Build PDF bytes with header, optional user photo, and report text."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return None

    try:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        margin = 50
        line_height = 14
        y = h - 50
        lines = text.split("\n")

        # Draw header: ==== , "AI-ASSISTED MENTAL HEALTH SCREENING REPORT" , ====
        header_count = min(3, len(lines))
        for i in range(header_count):
            line = lines[i]
            c.drawString(margin, y, line[:90] if len(line) > 90 else line)
            y -= line_height

        # Draw user photo below the header if provided
        if image_bytes:
            try:
                img = ImageReader(io.BytesIO(image_bytes))
                iw, ih = img.getSize()
                max_w, max_h = 180, 180
                scale = min(max_w / iw, max_h / ih, 1.0)
                dw, dh = iw * scale, ih * scale
                y -= 10
                c.drawImage(img, margin, y - dh, width=dw, height=dh)
                y = y - dh - 20
            except Exception:
                pass

        # Draw rest of report text
        for line in lines[header_count:]:
            if y < 50:
                c.showPage()
                y = h - 50
            c.drawString(margin, y, line[:90] if len(line) > 90 else line)
            y -= line_height
        c.save()
        return buf.getvalue()
    except Exception:
        return None


