import streamlit as st
import requests

st.set_page_config(page_title="Austin Hybrid Battery Receptionist", page_icon="🔋")
st.title("🔋 Austin Hybrid Battery AI Receptionist")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def ask_backend(msg):
    try:
        r = requests.post(
            "http://localhost:8080/chat",  # Change port if your Flask app uses a different one
            json={"message": msg},
            timeout=30
        )
        r.raise_for_status()
        return r.json().get("response", "No response from backend.")
    except Exception as e:
        return f"Error: {str(e)}"

with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Ask something or schedule an appointment:", "")
    submitted = st.form_submit_button("Send")
    if submitted and user_input.strip():
        st.session_state.chat_history.append(("You", user_input))
        response = ask_backend(user_input)
        st.session_state.chat_history.append(("Bot", response))

for speaker, msg in st.session_state.chat_history:
    if speaker == "You":
        st.markdown(f"<div style='color:green'><b>{speaker}:</b> {msg}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='color:blue'><b>{speaker}:</b> {msg}</div>", unsafe_allow_html=True)
