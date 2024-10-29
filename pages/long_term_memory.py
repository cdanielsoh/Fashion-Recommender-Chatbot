import streamlit as st

from chatbot_backend.core import retrieve_past_user_chat_log

st.write(retrieve_past_user_chat_log(st.session_state.state["user_id"]))