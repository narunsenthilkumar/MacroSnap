# 🥗 MacroSnap — AI Nutrition Buddy

MacroSnap is a modern Streamlit chat application powered by **Google Gemini** (Vision + Chat) and **Twilio** (WhatsApp). Enter your name and contact once, snap a photo or describe your meal, and get instant calorie and macro estimates. When you're done, hit **"Send to WhatsApp"** to get a complete daily digest delivered directly to your phone.

---

## ✨ Features

- **📸 Instant Food Vision**: Snap a photo using your camera or upload an image (`.jpg`, `.jpeg`, `.png`) to decode meals automatically.
- **💬 Conversational Memory**: Chat naturally with MacroSnap. Ask follow-up questions like *"How much protein was in that?"* or *"What healthy side can I add?"*.
- **🎯 Strictly Scoped Nutrition Persona**: MacroSnap's AI personality stays laser-focused on meals, nutrition, calories, and fitness.
- **📲 Direct WhatsApp Integration**: Rereads the entire conversation and compiles a formatted, emoji-friendly digest sent via Twilio's WhatsApp API.
- **⚡ Multi-Channel Support**: Seamlessly supports **WhatsApp** (Twilio), **Email** (Gmail SMTP), or **Telegram Bot**.
- **🎨 Modern, Polished UI**: Designed with clean typography, responsive layout, quick meal presets, and live connection status indicators.

---

## 📂 Project Structure

```
MacroSnap/
├── app.py                        # Main Streamlit application
├── prompts.py                    # AI persona, system prompts, and message templates
├── requirements.txt              # Project dependencies
├── .gitignore                    # Keeps secrets, venvs, and cache out of Git
├── README.md                     # Documentation and setup guide
└── .streamlit/
    └── secrets.toml.example      # Template for environment secrets
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- **Python 3.9+** installed
- A free **[Google AI Studio](https://aistudio.google.com)** account (for your Gemini API key)
- A free **[Twilio](https://www.twilio.com/try-twilio)** account (for WhatsApp Sandbox)

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
# Copy template to the active secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and fill in your keys:

```toml
# Google AI Studio API Key (https://aistudio.google.com)
GEMINI_API_KEY = "AIzaSy..."

# (Optional) Model name (defaults to gemini-2.5-flash)
# GEMINI_MODEL = "gemini-2.5-flash"

# Twilio Credentials (https://console.twilio.com)
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token_here"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
TWILIO_CONTENT_SID = "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# (Optional) Option B: Gmail SMTP
# GMAIL_ADDRESS = "your-email@gmail.com"
# GMAIL_APP_PASSWORD = "your-16-char-app-password"

# (Optional) Option C: Telegram Bot
# TELEGRAM_BOT_TOKEN = "your-bot-token"
```

> **Important**: Never commit `.streamlit/secrets.toml` to Git. It is already added to `.gitignore`.

---

## 📲 Setting up Twilio WhatsApp Sandbox

1. Go to your **Twilio Console** → **Messaging** → **Try it out** → **Send a WhatsApp message**.
2. From your personal phone, send the sandbox join keyword (e.g., `join happy-tiger`) to `+1 415 523 8886`.
3. In **Twilio Console** → **Messaging** → **Content Template Builder**, create a Text template:
   - Template Body: `Hi {{1}}, here's your MacroSnap summary:\n\n{{2}}`
   - Copy the generated **Content SID** (starts with `HX...`) into `TWILIO_CONTENT_SID`.

---

## ▶️ Running the App

```bash
streamlit run app.py
```

The app will launch at `http://localhost:8501`.

1. Enter your name and WhatsApp number (with country code, e.g., `+91XXXXXXXXXX`).
2. Say hi or click a quick sample meal.
3. Attach a picture of your breakfast, lunch, or dinner.
4. When you're ready, hit **📤 Send to WhatsApp**!

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push your repository to GitHub (ensure `.streamlit/secrets.toml` is ignored).
2. Visit **[share.streamlit.io](https://share.streamlit.io)** and connect your GitHub account.
3. Select your repository, branch, and specify `app.py` as the entry file.
4. Under **App Settings** → **Secrets**, copy the contents of your local `secrets.toml` and save.
5. Click **Deploy**!

---

## 🛡️ License

MIT License. Built for the CCBP AI Vision Chatbot Workshop.
