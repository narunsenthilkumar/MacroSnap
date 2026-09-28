"""
app.py - MacroSnap: AI Nutrition Buddy
A Streamlit chat application powered by Google Gemini (Vision + Chat) and Twilio (WhatsApp),
with optional Email (Gmail SMTP) and Telegram support.
"""

import html
import json
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import requests
import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client as TwilioClient

from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

# --- Page Configuration ---
st.set_page_config(
    page_title="MacroSnap - AI Nutrition Buddy",
    page_icon="🥗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Initialize session state keys safely
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- Custom Styling for Premium Look & Feel ---
st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Header styling */
    .app-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 4px;
    }
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10b981 0%, #059669 50%, #047857 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .app-tagline {
        color: #64748b;
        font-size: 0.95rem;
        margin-top: -6px;
        margin-bottom: 20px;
    }

    /* Onboarding Card */
    .onboarding-card {
        background: rgba(16, 185, 129, 0.04);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
    }

    /* User Profile Pill */
    .user-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        color: #334155;
        margin-bottom: 16px;
        font-weight: 500;
    }
    .user-pill .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
    }

    /* Quick Prompt Pills */
    .quick-pill {
        display: inline-block;
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.8rem;
        color: #475569;
        margin-right: 6px;
        margin-bottom: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .quick-pill:hover {
        background: #ecfdf5;
        border-color: #10b981;
        color: #047857;
    }

    /* Summary Card */
    .summary-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #10b981;
        border-radius: 10px;
        padding: 16px;
        margin: 12px 0;
        white-space: pre-wrap;
        font-family: inherit;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    /* Button overrides */
    div.stButton > button:first-child {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Helper: Safe Secret Retrieval with Environment Variable Fallback ---
def get_secret(key: str, default: str = "") -> str:
    """Safely retrieves a configuration key from st.secrets or os.environ."""
    try:
        if key in st.secrets:
            val = st.secrets[key]
            return str(val).strip() if val is not None else default
    except Exception:
        pass
    val = os.getenv(key)
    return str(val).strip() if val else default


# --- Configuration ---
MODEL_NAME = get_secret("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
TWILIO_ACCOUNT_SID = get_secret("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = get_secret("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = get_secret("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_CONTENT_SID = get_secret("TWILIO_CONTENT_SID")

# Optional alternative action tools
GMAIL_ADDRESS = get_secret("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = get_secret("GMAIL_APP_PASSWORD")
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")


# --- Cached Client Initializers ---
@st.cache_resource
def get_gemini_client(api_key: str):
    """Builds and caches the Gemini client so it survives Streamlit reruns."""
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


@st.cache_resource
def get_twilio_client(account_sid: str, auth_token: str):
    """Builds and caches the Twilio client for WhatsApp messaging."""
    if not account_sid or not auth_token:
        return None
    try:
        return TwilioClient(account_sid, auth_token)
    except Exception:
        return None


# --- Action Tool Dispatchers ---
def clean_whatsapp_text(text: str) -> str:
    """Collapses whitespace/newlines and caps length for WhatsApp messaging."""
    if not text:
        return "No nutrition summary available."
    cleaned = " ".join(text.split())
    return cleaned[:1500] + "..." if len(cleaned) > 1500 else cleaned


def send_whatsapp(to_number: str, user_name: str, summary: str, twilio_client_inst) -> tuple[bool, str]:
    """
    Sends WhatsApp summary via Twilio Content API (Template) or direct sandbox message.
    Expects {{1}} = name, {{2}} = summary for Content Template.
    """
    if not twilio_client_inst or not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False, "Twilio credentials not configured in secrets.toml."

    # Format destination number
    to_formatted = to_number.strip()
    if not to_formatted.startswith("+"):
        to_formatted = f"+{to_formatted}"
    whatsapp_to = f"whatsapp:{to_formatted}"

    # Strategy 1: Content Template API (as required by WhatsApp business rules)
    if TWILIO_CONTENT_SID:
        try:
            content_variables = json.dumps(
                {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
            )
            message = twilio_client_inst.messages.create(
                from_=TWILIO_WHATSAPP_FROM,
                to=whatsapp_to,
                content_sid=TWILIO_CONTENT_SID,
                content_variables=content_variables,
            )
            return True, message.sid
        except Exception as content_err:
            # Fall back to direct body messaging if template fails (e.g. sandbox testing)
            try:
                message = twilio_client_inst.messages.create(
                    from_=TWILIO_WHATSAPP_FROM,
                    to=whatsapp_to,
                    body=f"Hi {user_name}! Here is your MacroSnap summary:\n\n{summary}",
                )
                return True, message.sid
            except Exception:
                return False, str(content_err)

    # Strategy 2: Direct message body (for standard sandbox chat)
    try:
        message = twilio_client_inst.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=whatsapp_to,
            body=f"Hi {user_name}! Here is your MacroSnap summary:\n\n{summary}",
        )
        return True, message.sid
    except Exception as direct_err:
        return False, str(direct_err)


def send_email(to_address: str, user_name: str, summary: str) -> tuple[bool, str]:
    """Sends email summary via Gmail SMTP SSL (Option B)."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return False, "Gmail credentials not configured in secrets.toml (GMAIL_ADDRESS, GMAIL_APP_PASSWORD)."
    try:
        body = f"Hi {user_name},\n\nHere is your MacroSnap nutrition summary:\n\n{summary}\n\nStay healthy!\nMacroSnap 🥗"
        msg = MIMEText(body)
        msg["Subject"] = f"🥗 MacroSnap Daily Summary for {user_name}"
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_address

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True, "Email sent successfully"
    except Exception as err:
        return False, str(err)


def send_telegram(chat_id: str, user_name: str, summary: str) -> tuple[bool, str]:
    """Sends telegram summary via Telegram Bot API (Option C)."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "Telegram Bot Token not configured in secrets.toml (TELEGRAM_BOT_TOKEN)."
    try:
        text = f"🥗 *MacroSnap Summary for {user_name}*\n\n{summary}"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return True, "Telegram message sent successfully"
        return False, data.get("description", "Unknown Telegram error")
    except Exception as err:
        return False, str(err)


# --- Sidebar / Settings Panel ---
with st.sidebar:
    st.markdown("### ⚙️ MacroSnap Settings")

    # API Key Configuration helper (in case secrets.toml was not populated yet)
    effective_api_key = GEMINI_API_KEY
    if not effective_api_key:
        st.warning("⚠️ No `GEMINI_API_KEY` found in `.streamlit/secrets.toml`.")
        sidebar_key = st.text_input(
            "Enter Gemini API Key:",
            type="password",
            help="Get your free key from https://aistudio.google.com",
            key="user_provided_gemini_key",
        )
        if sidebar_key.strip():
            effective_api_key = sidebar_key.strip()
            st.session_state["override_api_key"] = effective_api_key
    elif "override_api_key" in st.session_state:
        effective_api_key = st.session_state["override_api_key"]

    # Model Selector
    model_choice = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        index=0,
        help="Default is gemini-2.5-flash as specified in MacroSnap guide.",
    )

    # Status indicators
    st.markdown("---")
    st.markdown("#### 🔌 Connection Status")
    if effective_api_key:
        st.caption("🟢 **Gemini AI:** Ready")
    else:
        st.caption("🔴 **Gemini AI:** Missing API Key")

    has_twilio = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)
    if has_twilio:
        st.caption("🟢 **Twilio WhatsApp:** Configured")
    else:
        st.caption("🟡 **Twilio WhatsApp:** Preview / Simulation Mode")

    if GMAIL_ADDRESS and GMAIL_APP_PASSWORD:
        st.caption("🟢 **Gmail SMTP:** Ready")
    if TELEGRAM_BOT_TOKEN:
        st.caption("🟢 **Telegram Bot:** Ready")

    # Reset Conversation Button
    st.markdown("---")
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        if "chat" in st.session_state:
            del st.session_state["chat"]
        st.rerun()

    if st.button("🚪 Logout / Re-onboard", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# Initialize Gemini and Twilio clients
gemini_client = get_gemini_client(effective_api_key)
twilio_client = get_twilio_client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# --- Chat Interface Helpers ---
def render_message(message: dict):
    """Renders a single message item inside Streamlit's chat UI."""
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role: str, kind: str, content):
    """Appends message to session state and renders it immediately."""
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])


def ask_gemini(parts) -> str:
    """Sends parts (text / images) to the existing Gemini chat session with graceful error handling."""
    if "chat" not in st.session_state or st.session_state.chat is None:
        return "Gemini chat session is not initialized. Please ensure your Gemini API key is valid."
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        err_msg = str(error)
        # Handle model not found fallback seamlessly
        if "404" in err_msg or "models/" in err_msg:
            try:
                fallback_chat = gemini_client.chats.create(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                st.session_state.chat = fallback_chat
                return fallback_chat.send_message(parts).text
            except Exception as inner_err:
                return f"Sorry, something went wrong with the Gemini API: {inner_err}"
        return f"Sorry, something went wrong: {error}"


# ==============================================================================
# Step 1: Onboarding Screen
# ==============================================================================
if "onboarded" not in st.session_state:
    st.markdown('<div class="app-header"><h1 class="app-title">🥗 MacroSnap</h1></div>', unsafe_allow_html=True)
    st.markdown('<p class="app-tagline">Snap it. Track it. Text yourself the results.</p>', unsafe_allow_html=True)

    if not effective_api_key:
        st.info(
            "👋 Welcome! Before starting, please provide your **Gemini API Key** in the sidebar (or add it to `.streamlit/secrets.toml`).",
            icon="🔑",
        )

    with st.form("onboarding_form"):
        st.markdown("### Let's get to know you 👋")
        name = st.text_input("Your Name", placeholder="e.g. Alex")

        action_channel = st.radio(
            "Preferred Delivery Channel",
            options=["WhatsApp", "Email", "Telegram"],
            index=0,
            horizontal=True,
            help="Choose where you'd like your daily nutrition summary sent.",
        )

        whatsapp_number = ""
        user_email = ""
        telegram_id = ""

        if action_channel == "WhatsApp":
            whatsapp_number = st.text_input(
                "WhatsApp Number (with country code)",
                placeholder="+91XXXXXXXXXX",
                help="Make sure this number has joined your Twilio Sandbox (e.g. text 'join your-code' to +14155238886).",
            )
        elif action_channel == "Email":
            user_email = st.text_input(
                "Your Email Address",
                placeholder="you@example.com",
                help="Summary will be sent to this email via Gmail SMTP.",
            )
        elif action_channel == "Telegram":
            telegram_id = st.text_input(
                "Your Telegram Chat ID",
                placeholder="123456789",
                help="Your numeric Telegram chat ID. Message your bot once to start.",
            )

        submitted = st.form_submit_button("Let's go 🚀", use_container_width=True)

    if submitted:
        channel_valid = (
            (action_channel == "WhatsApp" and bool(whatsapp_number.strip()))
            or (action_channel == "Email" and bool(user_email.strip()))
            or (action_channel == "Telegram" and bool(telegram_id.strip()))
        )

        if not name.strip() or not channel_valid:
            st.warning("Please fill in your name and delivery destination.")
        elif not effective_api_key:
            st.error("Please enter a valid Gemini API key in the sidebar to begin.")
        else:
            try:
                # Initialize Gemini chat session with persistent personality
                st.session_state.name = name.strip()
                st.session_state.channel = action_channel
                st.session_state.whatsapp_number = whatsapp_number.strip()
                st.session_state.email = user_email.strip()
                st.session_state.telegram_id = telegram_id.strip()

                active_model = model_choice or MODEL_NAME
                st.session_state.chat = gemini_client.chats.create(
                    model=active_model,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                st.session_state.messages = []
                st.session_state.onboarded = True
                st.rerun()
            except Exception as e:
                # Try fallback to gemini-2.0-flash if model creation had an issue
                try:
                    st.session_state.chat = gemini_client.chats.create(
                        model="gemini-2.0-flash",
                        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                    )
                    st.session_state.messages = []
                    st.session_state.onboarded = True
                    st.rerun()
                except Exception as ex:
                    st.error(f"Could not connect to Gemini: {ex}")
    st.stop()


# ==============================================================================
# Step 2: Main Chat & Action Screen
# ==============================================================================
header_col, button_col = st.columns([5, 3], vertical_alignment="center")

with header_col:
    st.markdown('<div class="app-header"><h1 class="app-title">🥗 MacroSnap</h1></div>', unsafe_allow_html=True)

channel_name = st.session_state.get("channel", "WhatsApp")
button_label = f"📤 Send to {channel_name}"

with button_col:
    # Button is disabled until at least one exchange has occurred beyond the welcome message
    send_disabled = len(st.session_state.messages) <= 2
    if st.button(button_label, disabled=send_disabled, use_container_width=True, type="primary"):
        with st.spinner("Summarizing your day with Gemini..."):
            summary = ask_gemini([SUMMARY_REQUEST_PROMPT])

        # Store last generated summary in session for inspection/copying
        st.session_state["last_summary"] = summary

        # Send via chosen channel
        success = False
        info = ""

        if channel_name == "WhatsApp":
            success, info = send_whatsapp(
                st.session_state.whatsapp_number,
                st.session_state.name,
                summary,
                twilio_client,
            )
        elif channel_name == "Email":
            success, info = send_email(
                st.session_state.email,
                st.session_state.name,
                summary,
            )
        elif channel_name == "Telegram":
            success, info = send_telegram(
                st.session_state.telegram_id,
                st.session_state.name,
                summary,
            )

        if success:
            st.success(f"Sent! Check your {channel_name} 📲")
        else:
            # If sending was blocked by sandbox/credentials, inform user and present summary directly
            st.warning(f"Delivery notice: {info}")
            st.info("Here is your generated nutrition summary ready for copy/paste:")
            st.markdown(f'<div class="summary-card">{html.escape(summary)}</div>', unsafe_allow_html=True)

# User status pill
dest = (
    st.session_state.whatsapp_number
    if channel_name == "WhatsApp"
    else (st.session_state.email if channel_name == "Email" else st.session_state.telegram_id)
)
st.markdown(
    f'<div class="user-pill"><span class="dot"></span> Logged in as <strong>{html.escape(st.session_state.name)}</strong> &nbsp;|&nbsp; Updates go to {channel_name}: {html.escape(dest)}</div>',
    unsafe_allow_html=True,
)

# Render Chat History
if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

# Quick sample meal buttons (helpful for quick testing without typing or taking a photo)
with st.expander("💡 Quick Sample Meals (Click to Test)", expanded=False):
    s_col1, s_col2, s_col3 = st.columns(3)
    sample_text = None
    with s_col1:
        if st.button("🥗 Greek Salad with Chicken"):
            sample_text = "I had a large Greek salad with grilled chicken breast, feta cheese, olives, cucumbers, and olive oil."
    with s_col2:
        if st.button("🍕 2 Slices of Pepperoni Pizza"):
            sample_text = "I ate 2 regular slices of pepperoni pizza and a small glass of iced tea."
    with s_col3:
        if st.button("🍳 Avocado Toast & 2 Eggs"):
            sample_text = "Breakfast was 2 scrambled eggs on sourdough toast with half an avocado and cherry tomatoes."

    if sample_text:
        add_message("user", "text", sample_text)
        with st.spinner("Crunching the numbers..."):
            answer = ask_gemini([sample_text])
        add_message("assistant", "text", answer)
        st.rerun()

# Optional Camera Input expander for mobile/webcam live snap
with st.expander("📷 Live Camera Snap (optional)", expanded=False):
    camera_pic = st.camera_input("Take a photo of your meal")
    if camera_pic is not None:
        if st.button("Analyze Captured Photo 🚀"):
            photo_bytes = camera_pic.getvalue()
            add_message("user", "image", photo_bytes)
            parts = [
                types.Part.from_bytes(data=photo_bytes, mime_type=camera_pic.type or "image/jpeg"),
                "What is this meal? Give me the estimated calories and macros (protein/carbs/fat).",
            ]
            with st.spinner("Crunching the numbers..."):
                answer = ask_gemini(parts)
            add_message("assistant", "text", answer)
            st.rerun()

# ==============================================================================
# Step 3: Chat Input (Text + File Upload via accept_file=True)
# ==============================================================================
user_input = st.chat_input(
    "Ask a question, or attach a photo of your meal",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))

    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("What is this meal? Give me the calories and macros.")

    with st.spinner("Crunching the numbers..."):
        answer = ask_gemini(parts)
    add_message("assistant", "text", answer)
