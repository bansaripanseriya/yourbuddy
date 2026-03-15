"""
Streamlit app: orchestrates UI (ui.py) and backend (api.py).
Upload image + name, submit to generate report, view output, download as PDF.
"""
import streamlit as st

from api import (
    REPORT_PATH,
    build_pdf_bytes,
    generate_and_save_report,
    get_report_content,
)
from ui import (
    apply_download_button_style,
    apply_page_config,
    login_modal,
    render_contact_page,
    render_download_section,
    render_empty_state_message,
    render_form,
    render_header,
    render_no_report_fallback,
    render_profile_page,
    render_report_output,
    render_sidebar,
)

# --- Page config and design ---
apply_page_config()
apply_download_button_style()

# --- Session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_username" not in st.session_state:
    st.session_state.login_username = None
if "show_login_for_download" not in st.session_state:
    st.session_state.show_login_for_download = False
if "report_generated_this_session" not in st.session_state:
    st.session_state.report_generated_this_session = False
if "show_login_modal" not in st.session_state:
    st.session_state.show_login_modal = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "main"

# --- Sidebar ---
render_sidebar(
    st.session_state.logged_in,
    st.session_state.login_username,
    st.session_state.get("current_page", "main"),
)

# --- My profile page (when logged in and navigated to profile) ---
if st.session_state.get("current_page") == "profile" and st.session_state.logged_in and st.session_state.login_username:
    render_profile_page(st.session_state.login_username)
    st.stop()

# --- Contact us page ---
if st.session_state.get("current_page") == "contact":
    render_contact_page(
        st.session_state.login_username if st.session_state.logged_in else None
    )
    st.stop()

# --- Header ---
render_header(st.session_state.logged_in, st.session_state.login_username)

# --- Login modal (when opened from header) ---
if st.session_state.get("show_login_modal") and not st.session_state.logged_in:
    login_modal()

# --- Form: name, image, submit ---
name, uploaded_file, submit = render_form()

if submit:
    if not name or not name.strip():
        st.warning("Please enter a name or Student ID.")
    elif not uploaded_file:
        st.warning("Please upload an image.")
    else:
        with st.spinner("Generating report..."):
            student_id = name.strip()
            image_bytes = uploaded_file.getvalue()
            report_text, err = generate_and_save_report(
                image_bytes, student_id, report_path=REPORT_PATH
            )
            if report_text:
                st.session_state["report_image_bytes"] = image_bytes
                st.session_state.report_generated_this_session = True
        if err:
            st.info(err)
        if report_text:
            st.success("Report generated and saved to clinical_report.txt")

# --- Report area: only after submit this session ---
if not st.session_state.get("report_generated_this_session", False):
    render_empty_state_message()
else:
    content = get_report_content(REPORT_PATH)
    if content is not None:
        render_report_output(content)
        report_image = st.session_state.get("report_image_bytes")

        def get_pdf_bytes():
            return build_pdf_bytes(content, report_image)

        def on_download_click():
            st.session_state.show_login_for_download = True
            st.rerun()

        render_download_section(
            logged_in=st.session_state.logged_in,
            show_login_for_download=st.session_state.get("show_login_for_download", False),
            pdf_bytes_callback=get_pdf_bytes,
            on_download_click_callback=on_download_click,
        )
    else:
        render_no_report_fallback()
