import streamlit as st
import requests
import json

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Author's Ghost", layout="wide")
st.title("Ai-  👻 Author's Ghost")

# Sidebar for PDF upload
st.sidebar.header("Upload a PDF Book")
with st.sidebar.form(key="upload_form"):
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    submit_upload = st.form_submit_button("Upload & Ingest")
    upload_status = st.empty()
    if submit_upload and uploaded_file:
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        with st.spinner("Uploading and processing PDF..."):
            res = requests.post(f"{API_URL}/upload_pdf/", files=files)
        if res.status_code == 200:
            upload_status.success("PDF uploaded and ingested successfully!")
        else:
            upload_status.error(f"Error: {res.json().get('message')}")

# Main chat area
st.header("Chat with the Author")
if "history" not in st.session_state:
    st.session_state["history"] = []

# Display chat history in a chat-like format
st.subheader("Conversation")

for turn in st.session_state["history"]:
    if turn["role"] == "user":
        # User bubble: blue background, white text
        st.markdown(f"<div style='text-align:right; margin-bottom:8px;'><span style='background:#1976D2; color:#fff; padding:10px 16px; border-radius:16px; display:inline-block; max-width:80%;'>{turn['content']}</span></div>", unsafe_allow_html=True)
    elif turn["role"] == "author":
        # Author bubble: light gray background, black text, with ghost emoji
        st.markdown(f"<div style='text-align:left; margin-bottom:8px;'><span style='background:#f5f5f5; color:#222; padding:10px 16px; border-radius:16px; display:inline-block; max-width:80%;'><b>👻 Author:</b> {turn['content']}</span></div>", unsafe_allow_html=True)


# Single input box at the bottom for next question (like ChatGPT)
st.markdown("---")


# Streaming chat handler

def handle_chat():
    user_input = st.session_state["chat_input"]
    if user_input:
        payload = {
            "question": user_input,
            "k": 3,
            "history": st.session_state["history"]
        }
        with st.spinner("Author's Ghost is replying..."):
            try:
                res = requests.post(f"{API_URL}/chat/", json=payload, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "(No response)")
                    st.session_state["history"].append({"role": "user", "content": user_input})
                    st.session_state["history"].append({"role": "author", "content": response_text.strip()})
                else:
                    st.error(f"Error: {res.text}")
            except Exception as e:
                st.error(f"Chat error: {e}")
        st.session_state["chat_input"] = ""

st.text_input(
    "Type your question and press Enter",
    key="chat_input",
    on_change=handle_chat
)
