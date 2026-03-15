"""
Design/UI: page config, styles, sidebar, form, and report display.
All Streamlit layout and styling live here.
"""
import html
import streamlit as st

from api import (
    create_user,
    get_user_profile,
    normalize_identifier,
    send_contact_email,
    send_verification_code,
    update_password,
    update_user_profile,
    user_exists,
    validate_login,
    verify_otp_and_reset_password,
)


def apply_page_config():
    """Set page title, icon, and layout."""
    st.set_page_config(
        page_title="YourBuddy - Mental Health Detector",
        page_icon="📋",
        layout="centered",
    )


def apply_download_button_style():
    """Inject CSS so download button matches primary theme and OTP boxes are narrow."""
    st.markdown("""
    <style>
        .stDownloadButton button, div[data-testid="stDownloadButton"] button {
            background-color: var(--primary-color, #FF4B4B) !important;
            color: white !important;
            font-weight: 500 !important;
            border: none !important;
            border-radius: 0.5rem !important;
            padding: 0.5rem 1rem !important;
            width: 100% !important;
            transition: opacity 0.2s ease;
        }
        .stDownloadButton button:hover, div[data-testid="stDownloadButton"] button:hover {
            opacity: 0.9;
            border: none !important;
        }
        .stDownloadButton button p, div[data-testid="stDownloadButton"] button p {
            color: white !important;
            font-weight: 500 !important;
        }
        /* Narrow OTP digit boxes - single-char inputs in form */
        input[maxlength="1"] {
            max-width: 2.5rem !important;
            text-align: center !important;
            font-size: 1.25rem !important;
            box-sizing: content-box !important;
        }
        /* Header Login | Sign up: text + underline only (no button look) - first row's last column */
        div[data-testid="stHorizontalBlock"]:first-of-type > div:last-child button {
            background: none !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            color: var(--primary-color, #FF4B4B) !important;
            text-decoration: underline !important;
            font-weight: 500 !important;
            padding: 0 !important;
            min-height: unset !important;
        }
        div[data-testid="stHorizontalBlock"]:first-of-type > div:last-child button:hover {
            background: none !important;
            border: none !important;
            text-decoration: underline !important;
            color: var(--primary-color, #FF4B4B) !important;
        }
        div[data-testid="stHorizontalBlock"]:first-of-type > div:last-child button p {
            color: inherit !important;
        }
        /* Sidebar: circular profile photo */
        .sidebar-avatar-wrap {
            display: flex;
            justify-content: center;
            margin-bottom: 1rem;
        }
        .sidebar-avatar-wrap .sidebar-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
        }
        .sidebar-avatar-placeholder {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: #e0e0e0;
            border: 2px dashed #999;
        }
        .sidebar-user-name {
            text-align: center;
            font-weight: 600;
            font-size: 0.95rem;
            margin-top: 0.5rem;
            margin-bottom: 0.75rem;
            word-break: break-word;
        }
        /* Sidebar active tab highlight */
        .sidebar-active-tab {
            background: var(--primary-color, #FF4B4B);
            color: white !important;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            text-align: center;
            margin-bottom: 0.25rem;
            font-weight: 600;
        }
        /* Sidebar: push Logout to bottom */
        section[data-testid="stSidebar"] > div:first-child {
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
        }
        .sidebar-logout-spacer {
            margin-top: auto !important;
            flex-shrink: 0;
        }
        /* My profile page: circular photo on top */
        .profile-page-avatar-wrap {
            display: flex;
            justify-content: center;
            margin-bottom: 1.5rem;
        }
        .profile-page-avatar-wrap .profile-page-avatar {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            object-fit: cover;
        }
        .profile-page-avatar-placeholder {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: #e0e0e0;
            border: 2px dashed #999;
        }
        .profile-page-avatar-wrap.clickable { cursor: pointer; }
        /* Edit profile photo dialog: make both Save and Cancel look like primary buttons */
        div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] button {
            background-color: var(--primary-color, #FF4B4B) !important;
            color: white !important;
            border: none !important;
            border-radius: 0.5rem !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            text-decoration: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] button:hover {
            opacity: 0.9;
            color: white !important;
            text-decoration: none !important;
        }
        div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] button p {
            color: white !important;
            text-decoration: none !important;
        }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar(logged_in: bool, login_username: str | None, current_page: str = "main"):
    """Render sidebar: photo, name, My profile, Home; Logout at bottom."""
    import base64
    with st.sidebar:
        if logged_in and login_username:
            profile = get_user_profile(login_username)
            if profile and profile.get("profile_photo"):
                pic = profile["profile_photo"]
                b64 = base64.b64encode(pic).decode("utf-8")
                fmt = "jpeg" if pic[:2] == b"\xff\xd8" else "png"
                st.markdown(
                    f'<div class="sidebar-avatar-wrap"><img src="data:image/{fmt};base64,{b64}" class="sidebar-avatar"/></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="sidebar-avatar-wrap sidebar-avatar-placeholder"></div>',
                    unsafe_allow_html=True,
                )
            display_name = (profile and profile.get("name") and profile.get("name").strip()) or login_username or "User"
            st.markdown(
                f'<div class="sidebar-user-name">{html.escape(display_name)}</div>',
                unsafe_allow_html=True,
            )
            st.divider()
            if current_page == "profile":
                st.markdown('<div class="sidebar-active-tab">My profile</div>', unsafe_allow_html=True)
            else:
                if st.button("**My profile**", key="sidebar_my_profile", use_container_width=True):
                    st.session_state.current_page = "profile"
                    st.session_state.pop("_profile_photo_modal_open", None)
                    st.session_state.pop("_profile_photo_modal_bytes", None)
                    st.session_state.pop("_profile_edit_photo_open", None)
                    st.session_state.pop("_profile_edit_photo_username", None)
                    st.rerun()
            if current_page == "main":
                st.markdown('<div class="sidebar-active-tab">Home</div>', unsafe_allow_html=True)
            else:
                if st.button("**Home**", key="sidebar_home", use_container_width=True):
                    st.session_state.current_page = "main"
                    st.rerun()
            if current_page == "contact":
                st.markdown('<div class="sidebar-active-tab">Contact us</div>', unsafe_allow_html=True)
            else:
                if st.button("**Contact us**", key="sidebar_contact", use_container_width=True):
                    st.session_state.current_page = "contact"
                    st.rerun()
            st.markdown('<div class="sidebar-logout-spacer"></div>', unsafe_allow_html=True)
            if st.button("Logout", key="sidebar_logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.login_username = None
                st.session_state.current_page = "main"
                st.rerun()


@st.dialog("Profile photo")
def _profile_photo_modal():
    """Show profile photo large with X to close."""
    import io
    pic = st.session_state.get("_profile_photo_modal_bytes")
    if pic:
        st.image(io.BytesIO(pic), use_container_width=True)

@st.dialog("Edit profile photo")
def _profile_edit_photo_dialog():
    """Upload a new profile photo; Save updates only the photo."""
    un = st.session_state.get("_profile_edit_photo_username")
    if not un:
        st.caption("Session expired.")
        if st.button("Close", key="edit_photo_close"):
            st.session_state.pop("_profile_edit_photo_open", None)
            st.session_state.pop("_profile_edit_photo_username", None)
            st.rerun()
        return
    photo_file = st.file_uploader("Choose a new photo", type=["png", "jpg", "jpeg"], key="edit_photo_upload")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save", key="edit_photo_save", type="primary", use_container_width=True):
            if photo_file:
                photo_bytes = photo_file.getvalue()
                ok, msg = update_user_profile(un, profile_photo=photo_bytes)
                if ok:
                    st.success(msg)
                    st.session_state.pop("_profile_edit_photo_open", None)
                    st.session_state.pop("_profile_edit_photo_username", None)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Select a photo first.")
    with col2:
        if st.button("Cancel", key="edit_photo_cancel", type="primary", use_container_width=True):
            st.session_state.pop("_profile_edit_photo_open", None)
            st.session_state.pop("_profile_edit_photo_username", None)
            st.rerun()


def render_profile_page(login_username: str):
    """Render the My profile page: circular photo on top (click to enlarge), then form. Username (email) is read-only."""
    import base64
    import io
    st.title("My profile")
    st.caption("Update your details. Email cannot be changed.")
    profile = get_user_profile(login_username)
    email = (profile.get("email") or login_username) if profile else login_username

    # Profile photo in circle on top
    has_photo = bool(profile and profile.get("profile_photo"))
    if has_photo:
        pic = profile["profile_photo"]
        b64 = base64.b64encode(pic).decode("utf-8")
        fmt = "jpeg" if pic[:2] == b"\xff\xd8" else "png"
        _c1, _c2, _c3 = st.columns([1, 2, 1])
        with _c2:
            st.markdown(
                f'<div class="profile-page-avatar-wrap clickable"><img src="data:image/{fmt};base64,{b64}" class="profile-page-avatar"/></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="profile-page-avatar-wrap profile-page-avatar-placeholder"></div>',
            unsafe_allow_html=True,
        )

    # Buttons beside each other: View full size (when has photo), Edit photo
    _b1, _b2 = st.columns(2)
    with _b1:
        if has_photo and st.button("View full size", key="profile_open_photo_modal", use_container_width=True):
            st.session_state._profile_photo_modal_open = True
            st.session_state._profile_photo_modal_bytes = profile["profile_photo"]
            st.session_state.pop("_profile_edit_photo_open", None)
            st.session_state.pop("_profile_edit_photo_username", None)
            st.rerun()
    with _b2:
        if st.button("Edit photo", key="profile_edit_photo_modal", use_container_width=True):
            st.session_state._profile_edit_photo_open = True
            st.session_state._profile_edit_photo_username = login_username
            st.session_state.pop("_profile_photo_modal_open", None)
            st.session_state.pop("_profile_photo_modal_bytes", None)
            st.rerun()

    with st.form("profile_form"):
        st.text_input("Email (username)", value=email, disabled=True, key="profile_email")
        name = st.text_input("Name", value=profile.get("name", "") if profile else "", placeholder="Your name", key="profile_name")
        bio = st.text_area("About you (max 500 characters)", value=profile.get("bio", "") if profile else "", placeholder="A short bio or about you...", height=100, max_chars=500, key="profile_bio")
        if bio:
            st.caption(f"{len(bio)} / 500 characters")
        age = st.number_input("Age", min_value=1, max_value=150, value=int(profile.get("age") or 0) or None, placeholder="Age", key="profile_age")
        phone = st.text_input("Phone number", value=profile.get("phone", "") if profile else "", placeholder="Phone", key="profile_phone")
        blood_group = st.text_input("Blood group", value=profile.get("blood_group", "") if profile else "", placeholder="e.g. A+, B-, O+", key="profile_blood")
        _gender_opts = ["Select gender", "Male", "Female", "Other", "Prefer not to say"]
        _current = (profile.get("gender", "") or "").strip() if profile else ""
        if not _current:
            _current = "Select gender"
        _gender_idx = _gender_opts.index(_current) if _current in _gender_opts else 0
        gender = st.selectbox("Gender", options=_gender_opts, index=_gender_idx, key="profile_gender")
        _dob_val = profile.get("date_of_birth", "") if profile else ""
        try:
            from datetime import datetime as _dt, date as _date
            _dob_default = _dt.strptime(_dob_val, "%Y-%m-%d").date() if _dob_val else None
        except Exception:
            _dob_default = None
        from datetime import date
        _min_dob = date(1900, 1, 1)
        date_of_birth = st.date_input("Date of birth", value=_dob_default, min_value=_min_dob, key="profile_dob")
        submit = st.form_submit_button("Save profile", type="primary")
    if submit:
        st.session_state.pop("_profile_photo_modal_open", None)
        st.session_state.pop("_profile_photo_modal_bytes", None)
        st.session_state.pop("_profile_edit_photo_open", None)
        st.session_state.pop("_profile_edit_photo_username", None)
        if bio and len((bio or "").strip()) > 500:
            st.error("Bio must be 500 characters or less.")
        else:
            dob_str = date_of_birth.strftime("%Y-%m-%d") if date_of_birth else ""
            _gender_val = "" if (gender == "Select gender" or not gender) else gender.strip()
            ok, msg = update_user_profile(
                login_username,
                name=name.strip() if name else "",
                age=int(age) if age else None,
                phone=phone.strip() if phone else "",
                blood_group=blood_group.strip() if blood_group else "",
                gender=_gender_val,
                bio=(bio.strip()[:500] if bio else ""),
                date_of_birth=dob_str,
            )
            if ok:
                st.success("Profile updated successfully.")
                st.rerun()
            else:
                st.error(msg)

    # Update password section
    st.divider()
    st.subheader("Update password")
    with st.form("update_password_form", clear_on_submit=True):
        current_pw = st.text_input("Current password", type="password", placeholder="Enter current password", key="profile_current_pw")
        new_pw = st.text_input("New password", type="password", placeholder="Enter new password (min 4 characters)", key="profile_new_pw")
        confirm_pw = st.text_input("Confirm new password", type="password", placeholder="Confirm new password", key="profile_confirm_pw")
        pw_submit = st.form_submit_button("Update password", type="primary")
    if pw_submit:
        st.session_state.pop("_profile_photo_modal_open", None)
        st.session_state.pop("_profile_photo_modal_bytes", None)
        st.session_state.pop("_profile_edit_photo_open", None)
        st.session_state.pop("_profile_edit_photo_username", None)
        if not (current_pw and new_pw and confirm_pw):
            st.error("Fill in all password fields.")
        elif not validate_login(login_username, current_pw):
            st.error("Current password is incorrect.")
        elif new_pw != confirm_pw:
            st.error("New password and confirmation do not match.")
        elif len(new_pw) < 4:
            st.error("New password must be at least 4 characters.")
        else:
            ok, msg = update_password(login_username, new_pw)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # Open at most one dialog per run, and only when no form was just submitted
    if not submit and not pw_submit:
        if st.session_state.get("_profile_photo_modal_open") and st.session_state.get("_profile_photo_modal_bytes"):
            _profile_photo_modal()
        elif st.session_state.get("_profile_edit_photo_open") and st.session_state.get("_profile_edit_photo_username"):
            _profile_edit_photo_dialog()


def render_contact_page(login_username: str | None = None):
    """Render Contact us page: form to send a query to the app owner's email. When logged in, email is pre-filled from username."""
    st.title("Contact us")
    st.caption("Send your query; it will be delivered to bansaripanseriya010@gmail.com.")
    profile = get_user_profile(login_username) if login_username else None
    default_name = (profile.get("name") or "").strip() if profile else ""
    default_email = login_username or ""
    with st.form("contact_form", clear_on_submit=True):
        contact_name = st.text_input("Your name", value=default_name, placeholder="Enter your name", key="contact_name")
        contact_email = st.text_input("Your email", value=default_email, disabled=bool(login_username), placeholder="Enter your email", key="contact_email")
        if login_username:
            st.caption("Email is from your logged-in account.")
        contact_message = st.text_area("Message", placeholder="Type your query or feedback...", height=150, key="contact_message")
        contact_submit = st.form_submit_button("Send message", type="primary")
    if contact_submit:
        name = (contact_name or "").strip()
        email = (contact_email or default_email or "").strip()
        message = (contact_message or "").strip()
        if not name:
            st.error("Please enter your name.")
        elif not email or "@" not in email:
            st.error("Please enter a valid email address.")
        elif not message:
            st.error("Please enter your message.")
        else:
            with st.spinner("Sending message..."):
                ok, msg = send_contact_email(name, email, message, logged_in_username=login_username)
            if ok:
                st.success(msg)
            else:
                st.error(msg)


def render_header(logged_in: bool, login_username: str | None):
    """Render main title and caption, with Login/Sign up on the right."""
    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.title("YourBuddy — Mental Health Detector")
        st.caption("Upload a face image and enter name to generate or view the clinical report.")
    with head_col2:
        st.write("")  # align with title
        if not logged_in:
            if st.button("Login | Sign up", key="header_login_btn"):
                st.session_state.show_login_modal = True
                st.rerun()


def render_form():
    """
    Render name input, image uploader, and Submit button.
    Returns (name_value, uploaded_file, submit_clicked).
    """
    name = st.text_input(
        "Name / Student ID",
        placeholder="Enter name",
        help="Name or identifier for the report",
    )
    uploaded_file = st.file_uploader(
        "Add image",
        type=["png", "jpg", "jpeg"],
        help="Upload a face image for emotion analysis",
    )
    submit = st.button("Submit", type="primary")
    return name, uploaded_file, submit


def render_empty_state_message():
    """Show message when no report has been generated this session."""
    st.info("Upload an image, enter a name, and click Submit to generate a report.")


def render_report_output(content: str):
    """Render report text area with content."""
    st.subheader("Report output")
    st.text_area(
        "Content of clinical_report.txt",
        value=content,
        height=400,
        disabled=True,
        label_visibility="collapsed",
    )


@st.dialog("Login or Sign up")
def login_modal():
    """Modal popup: Login, Sign up, and Forgot password tabs when user clicks Download without being logged in."""
    tab_login, tab_signup, tab_forgot = st.tabs(["Login", "Sign up", "Forgot password"])

    with tab_login:
        with st.form("download_login_form", clear_on_submit=True):
            username = st.text_input("Email", placeholder="Enter email", key="dl_username")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="dl_password")
            login_btn = st.form_submit_button("Login", type="primary")
        if login_btn:
            if validate_login(username or "", password or ""):
                st.session_state.logged_in = True
                st.session_state.login_username = (username or "").strip()
                st.session_state.show_login_for_download = False
                st.session_state.show_login_modal = False
                st.rerun()
            else:
                st.error("Invalid email/phone or password.")

    with tab_signup:
        with st.form("signup_form", clear_on_submit=True):
            st.caption("Create an account to download reports.")
            su_username = st.text_input("Email", placeholder="Enter email", key="su_username")
            su_password = st.text_input("Password", type="password", placeholder="Choose a password (min 4 characters)", key="su_password")
            su_confirm = st.text_input("Confirm password", type="password", placeholder="Confirm password", key="su_confirm")
            signup_btn = st.form_submit_button("Sign up", type="primary")
        if signup_btn:
            un = (su_username or "").strip()
            pw = su_password or ""
            if not un:
                st.error("Email or phone number is required.")
            elif not pw:
                st.error("Password is required.")
            elif len(pw) < 4:
                st.error("Password must be at least 4 characters.")
            elif pw != (su_confirm or ""):
                st.error("Passwords do not match.")
            elif user_exists(un):
                st.error("This email is already registered.")
            else:
                ok, msg = create_user(un, pw)
                if ok:
                    st.success(msg)
                    st.session_state.logged_in = True
                    st.session_state.login_username = un
                    st.session_state.show_login_for_download = False
                    st.rerun()
                else:
                    st.error(msg)

    with tab_forgot:
        # Step 2: OTP sent — show code + new password form
        if st.session_state.get("forgot_password_sent_to"):
            sent_to = st.session_state.forgot_password_sent_to
            # Mask for display: email -> first + *** + last 3 of local + @domain, phone -> ***4567890
            if "@" in sent_to:
                parts = sent_to.split("@")
                local = parts[0] if len(parts) > 1 else ""
                domain = parts[-1] if len(parts) > 1 else ""
                if len(local) >= 4:
                    masked = local[:1] + "***" + local[-3:] + "@" + domain
                else:
                    masked = local[:1] + "***@" + domain if local else "***"
            else:
                masked = "***" + sent_to[-4:] if len(sent_to) >= 4 else "***"
            # Insert zero-width space after @ so the text is not auto-linked as email
            _zw = "\u200b"
            if "@" in masked:
                masked_plain = masked.replace("@", "@" + _zw, 1)
            else:
                masked_plain = masked
            st.caption(f"Code sent to {masked_plain}")

            with st.form("forgot_password_otp_form", clear_on_submit=True):
                st.caption("Enter the 4-digit code")
                _, c0, c1, c2, c3, _ = st.columns([1, 0.6, 0.6, 0.6, 0.6, 1])
                with c0:
                    fp_d0 = st.text_input("Digit 1", max_chars=1, key="fp_c0", placeholder="", label_visibility="collapsed")
                with c1:
                    fp_d1 = st.text_input("Digit 2", max_chars=1, key="fp_c1", placeholder="", label_visibility="collapsed")
                with c2:
                    fp_d2 = st.text_input("Digit 3", max_chars=1, key="fp_c2", placeholder="", label_visibility="collapsed")
                with c3:
                    fp_d3 = st.text_input("Digit 4", max_chars=1, key="fp_c3", placeholder="", label_visibility="collapsed")
                fp_new = st.text_input("New password", type="password", placeholder="New password (min 4 characters)", key="fp_new")
                fp_confirm = st.text_input("Confirm new password", type="password", placeholder="Confirm new password", key="fp_confirm")
                fp_reset_btn = st.form_submit_button("Reset password", type="primary")
            # Auto-advance to next OTP box when 1 digit is entered (requires unsafe_allow_javascript)
            _otp_script = """
            <script>
            (function() {
                function attachOtpAdvance() {
                    var inputs = document.querySelectorAll('input[maxlength="1"]');
                    if (inputs.length < 4) return false;
                    for (var i = 0; i < inputs.length; i++) {
                        (function(idx) {
                            var inp = inputs[idx];
                            if (inp.dataset.otpAdvance === '1') return;
                            inp.dataset.otpAdvance = '1';
                            inp.addEventListener('input', function() {
                                if (inp.value.length >= 1 && idx < inputs.length - 1) {
                                    inputs[idx + 1].focus();
                                }
                            });
                            inp.addEventListener('keydown', function(e) {
                                if (e.key === 'Backspace' && inp.value === '' && idx > 0) {
                                    inputs[idx - 1].focus();
                                }
                            });
                        })(i);
                    }
                    return true;
                }
                function tryAttach() {
                    if (attachOtpAdvance()) return;
                    setTimeout(tryAttach, 200);
                }
                setTimeout(tryAttach, 300);
            })();
            </script>
            """
            try:
                st.html(_otp_script, unsafe_allow_javascript=True)
            except TypeError:
                # Older Streamlit: st.html may not have unsafe_allow_javascript
                st.markdown(_otp_script, unsafe_allow_html=True)
            if fp_reset_btn:
                code = "".join(((fp_d0 or "").strip(), (fp_d1 or "").strip(), (fp_d2 or "").strip(), (fp_d3 or "").strip()))
                new_pw = fp_new or ""
                if not code:
                    st.error("Please enter the 4-digit code.")
                elif len(code) != 4 or not code.isdigit():
                    st.error("Please enter a valid 4-digit code.")
                elif not new_pw:
                    st.error("New password is required.")
                elif len(new_pw) < 4:
                    st.error("Password must be at least 4 characters.")
                elif new_pw != (fp_confirm or ""):
                    st.error("Passwords do not match.")
                else:
                    # Use the same identifier we sent to (stored normalized); for update we need to pass it
                    ok, msg = verify_otp_and_reset_password(sent_to, code, new_pw)
                    if ok:
                        st.success(msg)
                        del st.session_state["forgot_password_sent_to"]
                        st.rerun()
                    else:
                        st.error(msg)

            if st.button("Use different email", key="fp_back", type="primary"):
                del st.session_state["forgot_password_sent_to"]
                st.rerun()
        else:
            # Step 1: Enter email/phone and send code
            with st.form("forgot_password_form", clear_on_submit=True):
                st.caption("Enter your email. We'll send a 4-digit code.")
                fp_username = st.text_input("Email", placeholder="Your email", key="fp_username")
                fp_send_btn = st.form_submit_button("Send verification code", type="primary")
            if fp_send_btn:
                un = (fp_username or "").strip()
                if not un:
                    st.error("Email or phone number is required.")
                else:
                    with st.spinner("Sending verification code..."):
                        ok, msg = send_verification_code(un)
                    if ok:
                        st.session_state.forgot_password_sent_to = normalize_identifier(un)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

def render_download_section(
    logged_in: bool,
    show_login_for_download: bool,
    pdf_bytes_callback,
    on_download_click_callback,
):
    """
    Render Download button (real download if logged in, else open login modal).
    pdf_bytes_callback() -> bytes | None for building PDF when logged in.
    on_download_click_callback() is called when Download is clicked while not logged in.
    """
    if logged_in:
        pdf_bytes = pdf_bytes_callback()
        if pdf_bytes:
            st.download_button(
                "📥 Download report as PDF",
                data=pdf_bytes,
                file_name="clinical_report.pdf",
                mime="application/pdf",
            )
        else:
            st.caption("Install reportlab for PDF download: pip install reportlab")
    else:
        if st.button("📥 Download report as PDF", type="primary"):
            on_download_click_callback()

    # Open login modal when user clicked Download (header login opens modal from app.py)
    if show_login_for_download and not logged_in:
        login_modal()
    return None, None, False


def render_no_report_fallback():
    """Show message when report_generated_this_session but file is missing."""
    st.info("No report yet. Upload an image, enter a name, and click Submit to generate a report.")
