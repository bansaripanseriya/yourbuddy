"""
Send OTP via email (SMTP) or SMS (Twilio).
Configure via .env or environment variables (python-decouple).
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from decouple import config


def _is_email(identifier: str) -> bool:
    return "@" in (identifier or "")


def send_otp_email(to_address: str, code: str) -> tuple[bool, str]:
    """
    Send OTP to email via SMTP. Returns (success, message).
    .env: SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, MAIL_FROM (optional).
    """
    host = config("SMTP_HOST", default="")
    user = config("SMTP_USER", default="")
    password = config("SMTP_PASSWORD", default="")
    if not all([host, user, password]):
        return False, "Email is not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD."
    port = int(config("SMTP_PORT", default="587"))
    from_addr = config("MAIL_FROM", default=user)
    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to_address
        msg["Subject"] = "YourBuddy - Password reset code"
        body = f"Your verification code for password reset is: {code}\n\nIt is valid for 10 minutes.\n\n— YourBuddy"
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, to_address, msg.as_string())
        return True, "Verification code sent to your email."
    except Exception as e:
        return False, f"Could not send email: {e}"


def send_contact_email(sender_name: str, sender_email: str, message: str, logged_in_username: str | None = None) -> tuple[bool, str]:
    """
    Send contact form submission to the app owner's email via SMTP.
    .env: CONTACT_EMAIL (recipient), or defaults to bansaripanseriya010@gmail.com.
    Uses same SMTP_HOST, SMTP_USER, SMTP_PASSWORD as OTP.
    If logged_in_username is set, the email body includes it so the recipient knows which user sent the query.
    """
    to_address = config("CONTACT_EMAIL", default="bansaripanseriya010@gmail.com").strip()
    host = config("SMTP_HOST", default="")
    user = config("SMTP_USER", default="")
    password = config("SMTP_PASSWORD", default="")
    if not all([host, user, password]):
        return False, "Email is not configured. Contact form cannot send."
    port = int(config("SMTP_PORT", default="587"))
    from_addr = config("MAIL_FROM", default=user)
    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to_address
        msg["Subject"] = "YourBuddy - Contact form query"
        body = f"Contact form submission\n\nFrom: {sender_name}\nEmail: {sender_email}\n"
        if logged_in_username:
            body += f"Logged-in user (username/email): {logged_in_username}\n"
        body += f"\nMessage:\n{message}"
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, to_address, msg.as_string())
        return True, "Your message has been sent. We'll get back to you soon."
    except Exception as e:
        return False, f"Could not send message: {e}"


def send_otp_sms(phone_number: str, code: str) -> tuple[bool, str]:
    """
    Send OTP via Twilio SMS. DISABLED until TWILIO_ACCOUNT_SID etc. are set in .env.
    Env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER.
    Phone number should be E.164 (e.g. +1234567890).
    """
    return False, "SMS is temporarily disabled. Please use email."
    # sid = config("TWILIO_ACCOUNT_SID", default="")
    # token = config("TWILIO_AUTH_TOKEN", default="")
    # from_number = config("TWILIO_FROM_NUMBER", default="")
    # if not all([sid, token, from_number]):
    #     return False, "SMS is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER."
    # try:
    #     from twilio.rest import Client
    #     client = Client(sid, token)
    #     to = phone_number if phone_number.startswith("+") else f"+{phone_number}"
    #     client.messages.create(body=f"YourBuddy password reset code: {code}. Valid 10 min.", from_=from_number, to=to)
    #     return True, "Verification code sent to your phone."
    # except ImportError:
    #     return False, "SMS requires: pip install twilio"
    # except Exception as e:
    #     return False, f"Could not send SMS: {e}"
