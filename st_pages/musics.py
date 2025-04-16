import streamlit as st
from src.WADPlayer import MIDIPlayer
from src.mus2mid import Mus2Mid
import os

if "player" not in st.session_state:
    st.session_state["player"] = None
    st.session_state["current_music"] = None

col1, col2, col3, col4, _ = st.columns([2, 1, 1, 3, 3], vertical_alignment="bottom")

music_names = st.session_state["wad"].musics

with col1:
    chosen_music = st.selectbox("Music", music_names)
temp_name = f"output/{chosen_music}.mus"
midi_name = f"output/{chosen_music}.mid"

if f"{chosen_music}.mid" not in os.listdir("output"):
    st.session_state["wad"].export_music(chosen_music, temp_name)
    m2m = Mus2Mid(temp_name)
    m2m.to_midi(midi_name)
    os.remove(temp_name)

# Create the player if it's not created yet or if the music is changed
if st.session_state["player"] is None:
    try:
        st.session_state["player"] = MIDIPlayer(midi_name)
    except Exception as e:
        st.error(f"Error loading music: {e}")
    st.session_state["current_music"] = chosen_music

if st.session_state["current_music"] != chosen_music:
    st.session_state["player"].stop()
    st.session_state["player"] = MIDIPlayer(midi_name)
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
