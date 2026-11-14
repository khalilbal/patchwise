from __future__ import annotations

import streamlit as st


def render_settings() -> None:
    st.title("Settings")
    st.text_input("AI API key", type="password")
    st.text_input("AI base URL", value="https://api.openai.com/v1")
    st.number_input("Scan timeout (seconds)", min_value=30, max_value=600, value=120)
