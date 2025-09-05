import streamlit as st
import json, os
from datetime import datetime
import pytz
import re
import time

# --- STYLING ---
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600&family=Poppins:wght@400;500&display=swap" rel="stylesheet">
    <style>
    .chat-bubble {
        transition: all 0.25s ease-in-out;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.1);
        border-radius: 24px;
    }
    .chat-bubble:hover {
        transform: scale(1.08);
        box-shadow: 
            0px 8px 20px rgba(0,0,0,0.25), 
            inset 0px 2px 6px rgba(255,255,255,0.3);
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIG ---
DATA_DIR = "chat_data"
HISTORY_DIR = "chat_history"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TZ = pytz.timezone("Asia/Karachi")


# --- FILE HELPERS ---
def chat_file(user1, user2):
    users = "_".join(sorted([user1, user2]))
    return os.path.join(DATA_DIR, f"{users}.json")

def history_file(filename):
    return os.path.join(HISTORY_DIR, filename)

def save_chat_to_history(messages):
    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
    with open(history_file(filename), "w") as f:
        json.dump(messages, f, indent=2)
    return filename

def load_history(filename):
    with open(history_file(filename), "r") as f:
        return json.load(f)


# --- CHAT LOAD & SAVE ---
def load_messages(u1, u2):
    path = chat_file(u1, u2)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning("⚠️ Chat file corrupted. Starting fresh.")
            return []
    return []

def save_messages(u1, u2, messages):
    with open(chat_file(u1, u2), "w") as f:
        json.dump(messages, f, indent=2)


# --- LINK PARSER ---
def make_links_clickable(text):
    url_pattern = re.compile(r"(https?://[^\s]+)")
    return url_pattern.sub(r'<a href="\\1" target="_blank" style="color:#007AFF;text-decoration:none;">\\1</a>', text)


# --- CHAT BUBBLE ---
def render_message_bubble(sender, message, timestamp, current_user, is_read=False):
    # Bubble alignment
    align = "right" if sender == current_user else "left"

    # Colors + Style
    if sender.lower() == current_user.lower():
        bubble_color = "linear-gradient(135deg, #FFEFEA, #FFD6D6)"  # Soft pink-peach gradient
        text_color = "#3A1F1F"  # Deep romantic brown
        font_weight = "500"  # Softer bold
        border_radius = "24px 24px 8px 24px"
    else:
        bubble_color = "linear-gradient(135deg, #F9F0FF, #EBDFFF)"  # Soft lavender gradient
        text_color = "#2F1E3E"  # Deep Mauve
        font_weight = "400"
        border_radius = "24px 24px 24px 8px"

    # Romantic Names
    if sender.lower() == "madam":
        display_name = "💖 Madam"
    elif sender.lower() == "meliora":
        display_name = "❤️‍🔥 Meliora"
    else:
        display_name = sender.capitalize()

    # Read ticks
    ticks = "<span style='color:#34B7F1;'>✔✔</span>" if (sender == current_user and is_read) else "<span style='color:gray;'>✔</span>" if sender == current_user else ""

    # Bubble HTML
    html = f"""
    <div style="display:flex; justify-content:{align}; margin:6px 0;">
        <div class="chat-bubble" style="
            background:{bubble_color};
            padding:14px 18px;
            border-radius:{border_radius};
            max-width:70%;
            font-family:'Ubuntu', sans-serif;
            font-size:15px;
            font-weight:{font_weight};
            line-height:1.5;
            color:{text_color};
            text-align:center;
        ">
            <b style="font-family:'Dancing Script', cursive; font-size:19px; color:{text_color};">{display_name}</b><br>
            {message}
            <div style="font-size:12px; color:gray; text-align:center;">🕒 {timestamp} {ticks}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)




# --- LOGIN ---
def load_users_from_secrets():
    return st.secrets["users"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login to Whisper Chat")
    USER_CREDENTIALS = load_users_from_secrets()
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in USER_CREDENTIALS and password == USER_CREDENTIALS[username]:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.partner = [u for u in USER_CREDENTIALS if u != username][0]
            st.success("✅ Login successful!")
            st.stop()
        else:
            st.error("❌ Invalid username or password")
    st.stop()


# --- CHAT UI ---
user = st.session_state.username
partner = st.session_state.partner

st.sidebar.title("💬 Chat Options")

# 🔥 Load messages first (so you can use them anywhere)
messages = load_messages(user, partner)

# SAVE CURRENT CHAT BUTTON
if st.sidebar.button("💾 Save Current Chat"):
    if messages:
        save_chat_to_history(messages)
        st.success("✅ Current chat saved to history!")
        time.sleep(1)
        st.rerun()
    else:
        st.warning("⚠️ No messages to save.")

# 🔍 SEARCH FEATURE
search_query = st.sidebar.text_input("🔍 Search Messages:")
history_files = sorted(os.listdir(HISTORY_DIR))
search_results = []
if search_query:
    for file in history_files:
        with open(history_file(file), "r") as f:
            chat = json.load(f)
            for msg in chat:
                if search_query.lower() in msg["text"].lower():
                    search_results.append((file, msg["timestamp"], msg["sender"], msg["text"]))
    st.sidebar.write(f"Found {len(search_results)} results:")
    for result in search_results[:5]:
        file, ts, snd, text = result
        st.sidebar.markdown(f"📂 **{file}**\n🕒 {ts} - {snd}: {text[:30]}...")

# NEW CHAT BUTTON
if st.sidebar.button("📝 New Chat"):
    save_chat_to_history(messages)
    save_messages(user, partner, [])
    st.success("Started a new chat!")
    st.rerun()

# HISTORY DROPDOWN
if history_files:
    selected = st.sidebar.selectbox("📜 Select Chat History:", history_files)

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📂 Load Chat"):
            messages = load_history(selected)
            save_messages(user, partner, messages)
            st.success(f"Loaded chat: {selected}")
            st.rerun()

    with col2:
        if st.button("🗑️ Delete History"):
            file_path = history_file(selected)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    st.success("✅ Chat history deleted successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Failed to delete history: {e}")
            else:
                st.warning("⚠️ File not found. Maybe already deleted.")







st.sidebar.info(f"Logged in as: {user}")
st.sidebar.info(f"Chatting with: {partner}")
st.title("Whisper Chat 🌸🫶")

# 🔥 Load messages and mark partner's as read
messages = load_messages(user, partner)
updated = False
for msg in messages:
    if msg["sender"] == partner and not msg.get("read", False):
        msg["read"] = True
        updated = True
if updated:
    save_messages(user, partner, messages)

# 🔥 Render chat
chat_container = st.container()
with chat_container:
    for m in messages:
        render_message_bubble(m["sender"], m["text"], m["timestamp"], user, m.get("read", False))

if st.button("🔄 Refresh Chat"):
    st.rerun()

# 🔥 Send message
user_input = st.chat_input("Type your message...")
if user_input:
    now = datetime.now(TZ)
    messages.append({
        "sender": user,
        "text": user_input,
        "timestamp": now.strftime("%Y-%m-%d %I:%M %p"),
        "ts": int(now.timestamp()),
        "read": False
    })
    save_messages(user, partner, messages)
    st.rerun()

# 🔥 Delete chat and related history
# 🔥 Delete chat
if st.button("🗑️ Delete Chat"):
    chat_path = chat_file(user, partner)
    if os.path.exists(chat_path):
        os.remove(chat_path)
        st.success("Chat deleted!")
        st.rerun()
    else:
        st.warning("⚠️ No chat found to delete.")

