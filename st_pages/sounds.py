import streamlit as st

import os
from loguru import logger


if "chosen_sound" not in st.session_state:
    st.session_state["chosen_sound"] = None
    st.session_state["sound_path"] = None

sound_list = st.session_state["wad"].sounds

col1, col2 = st.columns(2, vertical_alignment="bottom")
with col1:
    chosen_sound = st.selectbox("Sound", sound_list)
    sound_path = f"output/{chosen_sound}.wav"
    if chosen_sound + ".wav" not in os.listdir("output"):
        sound_path = st.session_state["wad"].export_sound(chosen_sound)
    st.session_state["sound_path"] = sound_path

with col2:
    st.audio(st.session_state["sound_path"])
