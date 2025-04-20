import streamlit as st
from src.WADPlayer import MIDIPlayer
from src.mus2mid import Mus2Mid
import os
from loguru import logger


if "music_path" not in st.session_state:
    st.session_state["player"] = None
    st.session_state["music_path"] = None
    st.session_state["chosen_music"] = None
    st.session_state["current_music"] = None

col1, col2, col3, col4, _ = st.columns([2, 1, 1, 3, 3], vertical_alignment="bottom")

music_names = st.session_state["wad"].musics

with col1:
    chosen_music = st.selectbox("Music", music_names)

    if chosen_music != st.session_state["chosen_music"]:

        music_path = st.session_state["wad"].export_music(chosen_music)

        if music_path.endswith(".mus"):
            m2m = Mus2Mid(music_path)

            new_path = m2m.to_midi()
            os.remove(music_path)
            st.session_state["music_path"] = new_path
        else:
            st.session_state["music_path"] = music_path

        logger.debug(music_path)
        st.session_state["chosen_music"] = chosen_music


# Create the player if it's not created yet or if the music is changed
if st.session_state["music_path"].endswith(".mid"):
    if st.session_state["player"] is None:
        try:
            st.session_state["player"] = MIDIPlayer(st.session_state["music_path"])
        except Exception as e:
            st.error(f"Error loading music: {e}.")
        st.session_state["current_music"] = chosen_music

    if st.session_state["current_music"] != chosen_music:
        st.session_state["player"].stop()
        st.session_state["player"] = MIDIPlayer(st.session_state["music_path"])
        st.session_state["current_music"] = chosen_music

    with col2:
        play_button = st.button("Play")
    if play_button:
        if st.session_state["player"] is not None:
            st.session_state["player"].play()
            with col4:
                st.write(f"Playing {chosen_music}...")
    with col3:
        stop_button = st.button("Stop")
    if stop_button:
        if st.session_state["player"] is not None:
            st.session_state["player"].stop()

elif st.session_state["music_path"].endswith(".ogg"):
    st.session_state["player"] = None
    with col2:
        st.audio(st.session_state["music_path"])
