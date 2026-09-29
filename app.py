"""
app.py - MacroSnap Universal AI Vision Suite
Supports all 4 project modes from the workshop:
  1. MacroSnap 🥗 (Nutrition & Macro Buddy)
  2. Snap & Study 📚 (Homework & Concept Explainer)
  3. Receipt Splitter 🧾 (Bill & Expense Tracker)
  4. Deadline Tracker ⏰ (Syllabus & Schedule Digest)

Multi-channel action tools:
  - Option A: WhatsApp (via Twilio)
  - Option B: Gmail (SMTP SSL - completely free)
  - Option C: Telegram Bot (Telegram API - completely free)
"""

import html
import json
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional, Tuple

import requests
import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client as TwilioClient

from prompts import (
    MODES,
    MACRO_SYSTEM_PROMPT,
    MACRO_WELCOME_TEMPLATE,
    MACRO_SUMMARY_PROMPT,
)

# --- Page Configuration ---
st.set_page_config(
    page_title="MacroSnap - Universal AI Vision Suite",
    page_icon="🥗",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Initialize session state keys safely
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "MacroSnap 🥗"

# --- Custom Styling for Premium Look & Feel ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .app-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 2px;
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
        margin-top: -4px;
        margin-bottom: 18px;
    }

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

    .mode-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        color: #065f46;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-left: 8px;
    }

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

# Action Tool Credentials
TWILIO_ACCOUNT_SID = get_secret("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = get_secret("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = get_secret("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_CONTENT_SID = get_secret("TWILIO_CONTENT_SID")

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
        return "No summary available."
    cleaned = " ".join(text.split())
    return cleaned[:1500] + "..." if len(cleaned) > 1500 else cleaned


def send_whatsapp(to_number: str, user_name: str, summary: str, twilio_client_inst) -> Tuple[bool, str]:
    """
    Sends WhatsApp summary via Twilio Content API (Template) or direct sandbox message.
    """
    if not twilio_client_inst or not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False, "Twilio credentials not configured in secrets.toml."

    # Clean and sanitize destination phone number into strict E.164 digits
    digits_only = "".join(c for c in to_number if c.isdigit())
    if not digits_only:
        return False, "Invalid WhatsApp phone number. Please include your country code (e.g. +91XXXXXXXXXX)."
    whatsapp_to = f"whatsapp:+{digits_only}"

    # Only use Content Template if it's a real Twilio Content SID (starts with HX)
    is_valid_content_sid = bool(
        TWILIO_CONTENT_SID
        and TWILIO_CONTENT_SID.strip().startswith("HX")
        and len(TWILIO_CONTENT_SID.strip()) == 34
    )

    if is_valid_content_sid:
        try:
            content_variables = json.dumps(
                {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
            )
            message = twilio_client_inst.messages.create(
                from_=TWILIO_WHATSAPP_FROM,
                to=whatsapp_to,
                content_sid=TWILIO_CONTENT_SID.strip(),
                content_variables=content_variables,
            )
            return True, message.sid
        except Exception as content_err:
            # If template delivery fails, fallback to direct text body
            try:
                body_text = f"Hi {user_name}! Here is your MacroSnap summary:\n\n{clean_whatsapp_text(summary)}"
                message = twilio_client_inst.messages.create(
                    from_=TWILIO_WHATSAPP_FROM,
                    to=whatsapp_to,
                    body=body_text,
                )
                return True, message.sid
            except Exception as fb_err:
                err_str = str(fb_err)
                if "Channel" in err_str or "63007" in err_str:
                    return False, (
                        "Twilio Sandbox error: You must join the sandbox from your phone first. "
                        "Open WhatsApp and send your sandbox join code (e.g. 'join <code>') to +14155238886. "
                        "Find your code in Twilio Console > Messaging > Try it out > Send a WhatsApp message."
                    )
                return False, f"Twilio template & direct fallback error: {fb_err}"

    # Direct messaging (used when Content Template is not configured or in sandbox)
    try:
        body_text = f"Hi {user_name}! Here is your MacroSnap summary:\n\n{clean_whatsapp_text(summary)}"
        message = twilio_client_inst.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=whatsapp_to,
            body=body_text,
        )
        return True, message.sid
    except Exception as direct_err:
        err_str = str(direct_err)
        if "Channel" in err_str or "63007" in err_str or "21608" in err_str:
            return False, (
                "Twilio Sandbox not activated for this number: "
                "1. Go to Twilio Console > Messaging > Try it out > Send a WhatsApp message. "
                "2. From your WhatsApp (+91...), send the join keyword (e.g. 'join <code>') to +14155238886. "
                "3. Once you receive Twilio's confirmation on WhatsApp, tap Send again!"
            )
        return False, str(direct_err)



def send_email(to_address: str, user_name: str, summary: str, mode_name: str) -> Tuple[bool, str]:
    """Sends email summary via Gmail SMTP SSL (Option B)."""
    gmail_user = (GMAIL_ADDRESS or st.session_state.get("override_gmail_address", "")).strip()
    gmail_pass = (GMAIL_APP_PASSWORD or st.session_state.get("override_gmail_password", "")).replace(" ", "").strip()

    if not gmail_user or not gmail_pass:
        return False, "Gmail credentials not configured. Please add GMAIL_ADDRESS and GMAIL_APP_PASSWORD."

    try:
        body = (
            f"Hi {user_name}!\n\n"
            f"Here is your {mode_name} summary from MacroSnap Suite:\n\n"
            f"----------------------------------------\n"
            f"{summary}\n"
            f"----------------------------------------\n\n"
            f"Generated with ❤️ by MacroSnap AI Suite."
        )
        msg = MIMEText(body)
        msg["Subject"] = f"📑 MacroSnap {mode_name} Digest for {user_name}"
        msg["From"] = gmail_user
        msg["To"] = to_address.strip()

        # Try Port 465 (SSL) first, with fallback to Port 587 (STARTTLS)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as server:
                server.login(gmail_user, gmail_pass)
                server.send_message(msg)
            return True, "Email sent successfully via Gmail SMTP!"
        except (smtplib.SMTPServerDisconnected, OSError):
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=12) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(gmail_user, gmail_pass)
                server.send_message(msg)
            return True, "Email sent successfully via Gmail SMTP!"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Gmail login failed (Bad Credentials): The 16-character App Password does not match "
            f"'{gmail_user}'. Please verify that GMAIL_ADDRESS is the exact Google account you used "
            "when generating this App Password at myaccount.google.com/apppasswords."
        )
    except Exception as err:
        return False, str(err)



def resolve_telegram_chat_id(bot_token: str, raw_input: str = "") -> Optional[int]:
    """Tries to resolve a Telegram username or fetch the latest sender ID via getUpdates."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        resp = requests.get(url, timeout=6)
        data = resp.json()
        if not data.get("ok"):
            return None
        clean_target = raw_input.strip().lstrip("@").lower() if raw_input else ""
        # 1. Look for matching username if provided
        for item in reversed(data.get("result", [])):
            msg = item.get("message") or item.get("channel_post") or item.get("my_chat_member")
            if not msg:
                continue
            sender = msg.get("from") or msg.get("chat")
            if not sender:
                continue
            username = (sender.get("username") or "").lower()
            if clean_target and clean_target == username:
                return sender.get("id")

        # 2. Otherwise return the most recent user who messaged the bot
        for item in reversed(data.get("result", [])):
            msg = item.get("message") or item.get("my_chat_member")
            if msg:
                sender = msg.get("from") or msg.get("chat")
                if sender and sender.get("id") and not sender.get("is_bot", False):
                    return sender.get("id")
    except Exception:
        pass
    return None


def send_telegram(chat_id: str, user_name: str, summary: str, mode_name: str) -> Tuple[bool, str]:
    """Sends telegram summary via Telegram Bot API (Option C)."""
    bot_token = TELEGRAM_BOT_TOKEN or st.session_state.get("override_telegram_token", "")
    if not bot_token:
        return False, "Telegram Bot Token not configured in secrets.toml."

    clean_id = str(chat_id).strip()

    # If user provided a username or non-numeric ID, try to resolve it from getUpdates
    if not clean_id.lstrip("-").isdigit():
        resolved = resolve_telegram_chat_id(bot_token, clean_id)
        if resolved:
            clean_id = str(resolved)
            st.session_state["telegram_id"] = clean_id
        else:
            return False, (
                "Telegram requires your numeric Chat ID (e.g. 123456789), not a username. "
                "👉 1) Open your bot on Telegram and tap 'Start' or send 'hi'. "
                "👉 2) Find your numeric ID using @userinfobot on Telegram."
            )

    try:
        text = f"📑 *MacroSnap {mode_name} Digest for {user_name}*\n\n{summary}"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        resp = requests.post(url, json={"chat_id": clean_id, "text": text}, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return True, "Telegram message sent successfully!"

        desc = data.get("description", "Unknown Telegram error")
        # Handle chat not found by attempting auto-resolution
        if "chat not found" in desc.lower() or "bot can't" in desc.lower():
            resolved = resolve_telegram_chat_id(bot_token, clean_id)
            if resolved and str(resolved) != clean_id:
                clean_id = str(resolved)
                st.session_state["telegram_id"] = clean_id
                retry_resp = requests.post(url, json={"chat_id": clean_id, "text": text}, timeout=10)
                if retry_resp.json().get("ok"):
                    return True, "Telegram message sent successfully!"

            return False, (
                f"{desc}. "
                "Note: A bot cannot message you first. Please open your bot on Telegram, "
                "press 'Start' (or send 'hi'), and enter your numeric Chat ID (from @userinfobot)."
            )
        return False, desc
    except Exception as err:
        return False, str(err)



# --- Sidebar / Mode Selector & Settings ---
with st.sidebar:
    st.markdown("### 🎛️ Vision Suite Modes")
    chosen_mode = st.selectbox(
        "Active Mode",
        options=list(MODES.keys()),
        index=list(MODES.keys()).index(st.session_state.current_mode),
        help="Switch between Nutrition, Study, Receipt Splitter, or Deadline Tracker.",
    )

    # When mode changes, prompt chat reload
    if chosen_mode != st.session_state.current_mode:
        st.session_state.current_mode = chosen_mode
        if "chat" in st.session_state:
            del st.session_state["chat"]
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Connection & Keys")

    # API Key Handling
    effective_api_key = GEMINI_API_KEY
    if not effective_api_key:
        st.warning("⚠️ No `GEMINI_API_KEY` in `secrets.toml`.")
        sidebar_key = st.text_input(
            "Gemini API Key:",
            type="password",
            help="Free key from https://aistudio.google.com",
            key="user_provided_gemini_key",
        )
        if sidebar_key.strip():
            effective_api_key = sidebar_key.strip()
            st.session_state["override_api_key"] = effective_api_key
    elif "override_api_key" in st.session_state:
        effective_api_key = st.session_state["override_api_key"]

    model_choice = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        index=0,
    )

    # Status Indicators
    st.markdown("#### 🔌 Channel Status")
    if effective_api_key:
        st.caption("🟢 **Gemini AI:** Connected")
    else:
        st.caption("🔴 **Gemini AI:** Key Required")

    has_twilio = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)
    st.caption(f"{'🟢' if has_twilio else '🟡'} **WhatsApp (Twilio):** {'Configured' if has_twilio else 'Simulation Mode'}")

    has_gmail = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD) or bool(st.session_state.get("override_gmail_address"))
    st.caption(f"{'🟢' if has_gmail else '⚪'} **Gmail (SMTP):** {'Configured' if has_gmail else 'Optional'}")

    has_tg = bool(TELEGRAM_BOT_TOKEN) or bool(st.session_state.get("override_telegram_token"))
    st.caption(f"{'🟢' if has_tg else '⚪'} **Telegram Bot:** {'Configured' if has_tg else 'Optional'}")

    # Optional Action Tool inputs if not in secrets.toml
    with st.expander("📬 Manual Action Tool Setup"):
        st.caption("Only needed if not specified in .streamlit/secrets.toml")
        m_gmail = st.text_input("Gmail Address", value=st.session_state.get("override_gmail_address", ""))
        m_pass = st.text_input("Gmail App Password (16 chars)", type="password", value=st.session_state.get("override_gmail_password", ""))
        m_tg = st.text_input("Telegram Bot Token", type="password", value=st.session_state.get("override_telegram_token", ""))
        if m_gmail:
            st.session_state["override_gmail_address"] = m_gmail
        if m_pass:
            st.session_state["override_gmail_password"] = m_pass
        if m_tg:
            st.session_state["override_telegram_token"] = m_tg

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
active_mode_info = MODES[st.session_state.current_mode]


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


def ensure_chat_session():
    """Initializes or restores the Gemini chat session for the active mode."""
    if "chat" not in st.session_state or st.session_state.chat is None:
        if not gemini_client:
            return None
        active_model = model_choice or MODEL_NAME
        try:
            st.session_state.chat = gemini_client.chats.create(
                model=active_model,
                config=types.GenerateContentConfig(system_instruction=active_mode_info["system_prompt"]),
            )
        except Exception:
            try:
                st.session_state.chat = gemini_client.chats.create(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=active_mode_info["system_prompt"]),
                )
            except Exception as e:
                st.error(f"Failed to create chat session: {e}")
                return None
    return st.session_state.chat


def ask_gemini(parts) -> str:
    """Sends parts to Gemini chat session with graceful error handling."""
    chat = ensure_chat_session()
    if chat is None:
        return "Gemini chat session could not be established. Please check your Gemini API key in the sidebar."
    try:
        return chat.send_message(parts).text
    except Exception as error:
        err_msg = str(error)
        if "404" in err_msg or "models/" in err_msg:
            try:
                fallback_chat = gemini_client.chats.create(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=active_mode_info["system_prompt"]),
                )
                st.session_state.chat = fallback_chat
                return fallback_chat.send_message(parts).text
            except Exception as inner:
                return f"Sorry, something went wrong: {inner}"
        return f"Sorry, something went wrong: {error}"


# ==============================================================================
# Step 1: Onboarding Screen
# ==============================================================================
if "onboarded" not in st.session_state:
    st.markdown(
        f'<div class="app-header"><h1 class="app-title">{active_mode_info["icon"]} {active_mode_info["title"]}</h1><span class="mode-badge">{st.session_state.current_mode}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<p class="app-tagline">{active_mode_info["tagline"]}</p>', unsafe_allow_html=True)

    if not effective_api_key:
        st.info(
            "👋 Welcome! Before starting, please provide your **Gemini API Key** in the sidebar (or add it to `.streamlit/secrets.toml`).",
            icon="🔑",
        )

    with st.form("onboarding_form"):
        st.markdown("### Profile & Delivery Setup")
        name = st.text_input("Your Name", placeholder="e.g. Alex")

        action_channel = st.radio(
            "Preferred Delivery Tool",
            options=["WhatsApp", "Email", "Telegram"],
            index=0,
            horizontal=True,
            help="Select how you would like to receive conversation digests and summaries.",
        )

        whatsapp_number = ""
        user_email = ""
        telegram_id = ""

        if action_channel == "WhatsApp":
            whatsapp_number = st.text_input(
                "WhatsApp Number (with country code)",
                placeholder="+91XXXXXXXXXX",
                help="Make sure this number has joined your Twilio Sandbox (e.g. text 'join <code-name>' to +14155238886).",
            )
        elif action_channel == "Email":
            user_email = st.text_input(
                "Your Email Address",
                placeholder="you@example.com",
                help="Summary will be sent directly via Gmail SMTP.",
            )
        elif action_channel == "Telegram":
            telegram_id = st.text_input(
                "Your Telegram Numeric Chat ID",
                placeholder="e.g. 583726194 (Numbers only, not username)",
                help="Enter your numeric User ID from @userinfobot. Do NOT enter @username.",
            )
            st.info(
                "💡 **How to get your Telegram Chat ID in 2 steps:**\n"
                "1. In Telegram, search for **`@userinfobot`** and tap Start — it will show your numeric **`Id: 123456789`**.\n"
                "2. Open your bot (e.g. search for its username) and tap **Start** (or send 'hi') so the bot has permission to message you."
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
            st.error("Please enter a valid Gemini API key in the sidebar to proceed.")
        else:
            st.session_state.name = name.strip()
            st.session_state.channel = action_channel
            st.session_state.whatsapp_number = whatsapp_number.strip()
            st.session_state.email = user_email.strip()
            st.session_state.telegram_id = telegram_id.strip()

            ensure_chat_session()
            st.session_state.messages = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()


# ==============================================================================
# Step 2: Main Interface & Action Dispatcher
# ==============================================================================
ensure_chat_session()

header_col, button_col = st.columns([5, 3], vertical_alignment="center")

with header_col:
    st.markdown(
        f'<div class="app-header"><h1 class="app-title">{active_mode_info["icon"]} {active_mode_info["title"]}</h1><span class="mode-badge">{st.session_state.current_mode}</span></div>',
        unsafe_allow_html=True,
    )

channel_name = st.session_state.get("channel", "WhatsApp")
button_label = f"📤 Send to {channel_name}"

with button_col:
    send_disabled = len(st.session_state.messages) <= 2
    if st.button(button_label, disabled=send_disabled, use_container_width=True, type="primary"):
        with st.spinner("Generating clean summary with Gemini..."):
            summary = ask_gemini([active_mode_info["summary_prompt"]])

        st.session_state["last_summary"] = summary
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
                active_mode_info["title"],
            )
        elif channel_name == "Telegram":
            success, info = send_telegram(
                st.session_state.telegram_id,
                st.session_state.name,
                summary,
                active_mode_info["title"],
            )

        if success:
            st.success(f"Sent! Check your {channel_name} 📲")
        else:
            st.warning(f"Delivery notice: {info}")
            st.info("Here is your generated summary ready for copy/paste:")
            st.markdown(f'<div class="summary-card">{html.escape(summary)}</div>', unsafe_allow_html=True)

# User status pill
dest = (
    st.session_state.whatsapp_number
    if channel_name == "WhatsApp"
    else (st.session_state.email if channel_name == "Email" else st.session_state.telegram_id)
)
st.markdown(
    f'<div class="user-pill"><span class="dot"></span> <strong>{html.escape(st.session_state.name)}</strong> &nbsp;|&nbsp; {channel_name}: {html.escape(dest)} &nbsp;|&nbsp; Mode: {st.session_state.current_mode}</div>',
    unsafe_allow_html=True,
)

# Render Chat History
if not st.session_state.messages:
    welcome_text = active_mode_info["welcome_template"].format(
        name=st.session_state.name, channel=channel_name
    )
    add_message("assistant", "text", welcome_text)
else:
    for message in st.session_state.messages:
        render_message(message)

# Quick sample buttons tailored for current mode
with st.expander("💡 Quick Test Presets (Click to Test)", expanded=False):
    cols = st.columns(len(active_mode_info["samples"]))
    sample_text = None
    for idx, (label, prompt_val) in enumerate(active_mode_info["samples"]):
        with cols[idx]:
            if st.button(label, use_container_width=True, key=f"sample_{idx}"):
                sample_text = prompt_val

    if sample_text:
        add_message("user", "text", sample_text)
        with st.spinner("Analyzing with Gemini..."):
            answer = ask_gemini([sample_text])
        add_message("assistant", "text", answer)
        st.rerun()

# Optional Camera Input expander
with st.expander("📷 Live Camera Snap (optional)", expanded=False):
    camera_pic = st.camera_input("Take a photo")
    if camera_pic is not None:
        if st.button("Analyze Captured Photo 🚀", key="analyze_camera_btn"):
            photo_bytes = camera_pic.getvalue()
            add_message("user", "image", photo_bytes)
            parts = [
                types.Part.from_bytes(data=photo_bytes, mime_type=camera_pic.type or "image/jpeg"),
                "Analyze this image according to your role and provide the full breakdown.",
            ]
            with st.spinner("Analyzing image..."):
                answer = ask_gemini(parts)
            add_message("assistant", "text", answer)
            st.rerun()

# ==============================================================================
# Step 3: Chat Input (Text + File Upload via accept_file=True)
# ==============================================================================
user_input = st.chat_input(
    f"Ask {active_mode_info['title']} a question, or attach a photo...",
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
        parts.append("Analyze this image according to your role and provide the full breakdown.")

    with st.spinner("Crunching the details..."):
        answer = ask_gemini(parts)
    add_message("assistant", "text", answer)
