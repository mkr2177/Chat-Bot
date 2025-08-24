import streamlit as st
from backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage
from datetime import datetime
import uuid
import json

# ------------------ Utility Functions ------------------ #
def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id, "New Conversation")
    st.session_state["message_history"] = []

def add_thread(thread_id, title):
    if thread_id not in [t["id"] for t in st.session_state["chat_threads"]]:
        st.session_state["chat_threads"].append({"id": thread_id, "title": title})

def load_conversation(thread_id):
    return chatbot.get_state(config={"configurable": {"thread_id": thread_id}}).values["messages"]

# ------------------ Session State Setup ------------------ #
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    # Convert retrieved threads into dict format with default titles
    st.session_state["chat_threads"] = [
        {"id": str(t), "title": "Old Conversation"} for t in retrieve_all_threads()
    ]

add_thread(st.session_state["thread_id"], "New Conversation")

# ------------------ Custom CSS for Chat UI ------------------ #
st.markdown("""
    <style>
    .chat-container {
        display: flex;
        margin: 8px 0;
        width: 100%;
    }
    .chat-bubble {
        padding: 10px 15px;
        border-radius: 12px;
        max-width: 70%;
        word-wrap: break-word;
        font-size: 15px;
        position: relative;
    }
    .timestamp {
        font-size: 11px;
        color: gray;
        margin-top: 2px;
    }
    .user-bubble {
        background-color: #DCF8C6;
        border: 1px solid #ccc;
        margin-left: auto;
        text-align: right;
    }
    .assistant-bubble {
        background-color: #E6E6FA;
        border: 1px solid #ccc;
        margin-right: auto;
        text-align: left;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ Sidebar ------------------ #
st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("➕ New Chat", key="new_chat"):
    reset_chat()

st.sidebar.header("My Conversations")

for thread in st.session_state["chat_threads"][::-1]:
    if st.sidebar.button(thread["title"], key=thread["id"]):
        st.session_state["thread_id"] = thread["id"]
        messages = load_conversation(thread["id"])

        temp_messages = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            temp_messages.append({"role": role, "content": msg.content, "time": ""})

        st.session_state["message_history"] = temp_messages

# ------------------ Buttons for Clear & Download ------------------ #
col1, col2 = st.columns(2)
with col1:
    if st.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state["message_history"] = []
        st.rerun()
with col2:
    if st.session_state["message_history"]:
        chat_json = json.dumps(st.session_state["message_history"], indent=2)
        st.download_button("⬇️ Download Chat", chat_json, "chat_history.json", "application/json", key="download_chat")

# ------------------ Display Chat History ------------------ #
for message in st.session_state["message_history"]:
    timestamp = message.get("time", "")
    if message["role"] == "user":
        st.markdown(f"""
            <div class="chat-container">
                <div class="chat-bubble user-bubble">{message['content']}
                    <div class="timestamp">{timestamp}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="chat-container">
                <div class="chat-bubble assistant-bubble">{message['content']}
                    <div class="timestamp">{timestamp}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------ Chat Input ------------------ #
user_input = st.chat_input("Type here")

if user_input:
    # Add user message
    now = datetime.now().strftime("%H:%M")
    st.session_state["message_history"].append({"role": "user", "content": user_input, "time": now})
    st.markdown(f"""
        <div class="chat-container">
            <div class="chat-bubble user-bubble">{user_input}
                <div class="timestamp">{now}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # If this is the first message in this thread → set as thread title
    if len(st.session_state["message_history"]) == 1:
        for thread in st.session_state["chat_threads"]:
            if thread["id"] == st.session_state["thread_id"]:
                thread["title"] = user_input[:40] + ("..." if len(user_input) > 40 else "")

    # Typing indicator
    typing_placeholder = st.empty()
    typing_placeholder.markdown("🤖 Assistant is typing...")

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    # ---- Stream Assistant Response ----
    full_response = ""
    stream_placeholder = st.empty()

    for message_chunk, metadata in chatbot.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=CONFIG,
        stream_mode="messages"
    ):
        chunk_text = message_chunk.content
        full_response += chunk_text
        stream_placeholder.markdown(
            f"""
            <div class="chat-container">
                <div class="chat-bubble assistant-bubble">{full_response}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Remove typing indicator
    typing_placeholder.empty()

    # Add assistant message to history
    now = datetime.now().strftime("%H:%M")
    st.session_state["message_history"].append({"role": "assistant", "content": full_response, "time": now})
