# 🌟 MacroSnap — Universal AI Vision Suite

MacroSnap is a versatile Streamlit application powered by **Google Gemini** (Vision + Chat) and **Multi-Channel Dispatch** (**WhatsApp**, **Gmail**, and **Telegram**). 

Built for the **CCBP AI Vision Chatbot Workshop**, this project unifies all 4 flagship project ideas into a single seamless suite with zero model training, OpenCV, or MediaPipe overhead.

---

## 🎛️ 4 Interactive AI Vision Modes

| Mode | Icon | Description | Core Action |
| :--- | :---: | :--- | :--- |
| **MacroSnap** | 🥗 | Snap a meal or food photo to get instant estimated calories and macros (protein, carbs, fat). | Sends complete daily nutrition & macro recap. |
| **Snap & Study** | 📚 | Photograph a diagram, homework problem, textbook page, or handwritten notes for plain-language explanations. | Sends high-yield revision sheet & formulas. |
| **Receipt Splitter** | 🧾 | Photograph a receipt, check, or invoice to itemize costs, compute tax/tip, and split shares fairly. | Sends itemized financial breakdown & split balances. |
| **Deadline Tracker** | ⏰ | Photograph a syllabus, timetable, or assignment notice to extract upcoming dates and tests. | Sends prioritized chronological deadline checklist. |

---

## 📬 3 Integrated Delivery Channels (Action Tools)

- **Option A: WhatsApp (via Twilio)**: Sends formatted digests using Twilio's WhatsApp Content Template API or sandbox messaging.
- **Option B: Gmail (via SMTP - Completely Free)**: Sends email summaries via Python's built-in `smtplib` using Google App Passwords.
- **Option C: Telegram Bot (Completely Free)**: Sends instant messages to any Telegram chat via the Telegram Bot API.
- **In-App Copy / Preview**: Instant copyable card displayed directly in the app so you are never blocked during local testing or evaluation.

---

## 📂 Project Structure

```
MacroSnap/
├── app.py                        # Complete Streamlit multi-mode application
├── prompts.py                    # AI personas, system prompts, and templates for all 4 modes
├── requirements.txt              # Project dependencies
├── .gitignore                    # Keeps secrets.toml, venvs, and cache out of Git
├── README.md                     # Documentation and setup guide
└── .streamlit/
    └── secrets.toml.example      # Secrets template (never committed)
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- **Python 3.9+** installed
- A free **[Google AI Studio](https://aistudio.google.com)** account (for your Gemini API key)
- *(Optional)* A free **[Twilio](https://www.twilio.com/try-twilio)** account for WhatsApp Sandbox
- *(Optional)* A Gmail address with an [App Password](https://myaccount.google.com/apppasswords) for Email
- *(Optional)* A Telegram bot token from [@BotFather](https://t.me/BotFather)

### 2. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/<your-username>/MacroSnap.git
cd MacroSnap

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔑 Configuration & Secrets

Create your local secrets configuration:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and configure your credentials:

```toml
# 1. Google Gemini (Required)
GEMINI_API_KEY = "AIzaSy..."

# 2. WhatsApp via Twilio (Option A)
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token_here"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
TWILIO_CONTENT_SID = "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 3. Gmail SMTP (Option B - Free)
# GMAIL_ADDRESS = "your-email@gmail.com"
# GMAIL_APP_PASSWORD = "your-16-char-app-password"

# 4. Telegram Bot (Option C - Free)
# TELEGRAM_BOT_TOKEN = "123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
```

> **Security Note**: `.streamlit/secrets.toml` is included in `.gitignore` and is never committed to GitHub.

---

## ▶️ Running the App

```powershell
# Using the virtual environment directly:
.\venv\Scripts\streamlit.exe run app.py
```

The app opens at `http://localhost:8501`.

1. Choose your active mode from the sidebar (**MacroSnap 🥗**, **Snap & Study 📚**, **Receipt Splitter 🧾**, or **Deadline Tracker ⏰**).
2. Enter your name and contact destination in the onboarding form.
3. Test with text questions, quick sample presets, or upload a photo.
4. Click **📤 Send to [Channel]** to deliver the AI-generated digest!

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push your repository to GitHub (ensure `.streamlit/secrets.toml` is ignored).
2. Visit **[share.streamlit.io](https://share.streamlit.io)** and log in with GitHub.
3. Click **New app**, select your repository, branch, and set `app.py` as the entrypoint.
4. Under **App Settings** → **Secrets**, paste your secrets from `secrets.toml`.
5. Click **Deploy**!

---

## 🛡️ License

MIT License. Built for the CCBP AI Vision Chatbot Workshop.
