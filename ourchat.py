import streamlit as st
import json, os, wave, time, re
from datetime import datetime
import pytz
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av

# --- CONFIG ---
DATA_DIR = "chat_data"
HISTORY_DIR = "chat_history"
VOICE_DIR = "voice_messages"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(VOICE_DIR, exist_ok=True)

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TZ = pytz.timezone("Asia/Karachi")

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

# --- FILE HELPERS ---
def chat_file(user1, user2):
    users = "_".join(sorted([user1, user2]))
    return os.path.join(DATA_DIR, f"{users}.json")

def history_file(filename):
    return os.path.join(HISTORY_DIR, filename)

def save_chat_to_history(messages):
    existing = sorted(os.listdir(HISTORY_DIR))
    chat_count = len(existing) + 1
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"Ms_Chat{chat_count}_{date_str}.json"
    with open(history_file(filename), "w") as f:
        json.dump(messages, f, indent=2)
    return filename

def load_history(filename):
    with open(history_file(filename), "r") as f:
        return json.load(f)

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

def make_links_clickable(text):
    url_pattern = re.compile(r"(https?://[^\s]+)")
    return url_pattern.sub(r'<a href="\\1" target="_blank" style="color:#007AFF;text-decoration:none;">\\1</a>', text)

# --- CHAT BUBBLE ---
def render_message_bubble(sender, message, timestamp, current_user, is_read=False):
    align = "right" if sender == current_user else "left"

    if sender.lower() == current_user.lower():
        bubble_color = "linear-gradient(135deg, #FFEFEA, #FFD6D6)"
        text_color = "#3A1F1F"
        font_weight = "500"
        border_radius = "24px 24px 8px 24px"
    else:
        bubble_color = "linear-gradient(135deg, #F9F0FF, #EBDFFF)"
        text_color = "#2F1E3E"
        font_weight = "400"
        border_radius = "24px 24px 24px 8px"

    if sender.lower() == "madam":
        display_name = "💖 Madam"
    elif sender.lower() == "meliora":
        display_name = "❤️‍🔥 Meliora"
    else:
        display_name = sender.capitalize()

    ticks = "<span style='color:#34B7F1;'>✔✔</span>" if (sender == current_user and is_read) else "<span style='color:gray;'>✔</span>" if sender == current_user else ""

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

    # Play audio if message is a voice note
    if ".wav" in message:
        try:
            st.audio(message.replace("[Voice Message](", "").replace(")", ""))
        except:
            st.write("🎵 Voice message (file missing)")

# --- LOGIN ---
def load_users_from_secrets():
    return st.secrets["users"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login to Mychat pro")
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
messages = load_messages(user, partner)

# SAVE CHAT
if st.sidebar.button("💾 Save Current Chat"):
    if messages:
        if "selected_history" in st.session_state and st.session_state.selected_history:
            file_path = history_file(st.session_state.selected_history)
            with open(file_path, "w") as f:
                json.dump(messages, f, indent=2)
            st.success(f"✅ Chat updated in {st.session_state.selected_history}!")
        else:
            save_chat_to_history(messages)
            st.success("✅ Current chat saved to NEW history!")
        time.sleep(1)
        st.rerun()
    else:
        st.warning("⚠️ No messages to save.")

# HISTORY MANAGEMENT
history_files = sorted(os.listdir(HISTORY_DIR))
if history_files:
    selected = st.sidebar.selectbox("📜 Select Chat History:", history_files)
    st.session_state.selected_history = selected
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

# Mark partner messages as read
updated = False
for msg in messages:
    if msg["sender"] == partner and not msg.get("read", False):
        msg["read"] = True
        updated = True
if updated:
    save_messages(user, partner, messages)

# CHAT MESSAGES
chat_container = st.container()
with chat_container:
    for m in messages:
        render_message_bubble(m["sender"], m["text"], m["timestamp"], user, m.get("read", False))

if st.button("🔄 Refresh Chat"):
    st.rerun()

# SEND TEXT MESSAGE
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

# --- VOICE MESSAGE FEATURE ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
        audio = frame.to_ndarray()
        self.frames.append(audio)
        return frame

st.subheader("🎤 Send a Voice Message")
webrtc_ctx = webrtc_streamer(
    key="send-audio",
    mode="sendonly",
    audio_receiver_size=256,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

if webrtc_ctx and webrtc_ctx.state.playing:
    processor = webrtc_ctx.audio_processor
    if st.button("📩 Send Voice Message"):
        if processor and processor.frames:
            now = datetime.now(TZ)
            filename = f"{user}_{int(now.timestamp())}.wav"
            filepath = os.path.join(VOICE_DIR, filename)

            wf = wave.open(filepath, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"".join([f.tobytes() for f in processor.frames]))
            wf.close()

            messages.append({
                "sender": user,
                "text": f"[Voice Message]({filepath})",
                "timestamp": now.strftime("%Y-%m-%d %I:%M %p"),
                "ts": int(now.timestamp()),
                "read": False
            })
            save_messages(user, partner, messages)
            st.success("✅ Voice message sent!")
            st.rerun()
        else:
            st.warning("⚠️ No voice recorded yet.")

# DELETE CHAT BUTTON
if st.button("🗑️ Delete Chat"):
    chat_path = chat_file(user, partner)
    if os.path.exists(chat_path):
        os.remove(chat_path)
        st.success("Chat deleted!")
        st.rerun()
    else:
        st.warning("⚠️ No chat found to delete.")
