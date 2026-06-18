import sys
import streamlit as st
from src.WADPlayer import WinMIDIPlayer, MIDIWavConverter
from src.mus2mid import Mus2Mid
import os

if "music_path" not in st.session_state:
    st.session_state["player"] = None
    st.session_state["music_path"] = None
    st.session_state["chosen_music"] = None
    st.session_state["current_music"] = None

col1, col2, col3, col4 = st.columns([2, 1, 1, 1], vertical_alignment="bottom")

music_names = st.session_state["wad"].musics


with col1:
    chosen_music = st.selectbox("Music", music_names)

    if chosen_music != st.session_state["chosen_music"]:
        music_path = st.session_state["wad"].export_music(chosen_music)

        # If the music is in MUS format, convert it to MIDI first
        if music_path.endswith(".mus"):
            m2m = Mus2Mid(music_path)

            new_path = m2m.to_midi()
            os.remove(music_path)
            st.session_state["music_path"] = new_path
        # Wad files can contain midi, mp3, etc...
        else:
            st.session_state["music_path"] = music_path

        st.session_state["chosen_music"] = chosen_music

# First, what is the music extension?
if st.session_state["music_path"] is not None:
    music_name, music_extension = os.path.splitext(
        st.session_state["music_path"])


if music_extension == ".mid" and sys.platform == "win32":
    if st.session_state["player"] is None:
        try:
            st.session_state["player"] = WinMIDIPlayer(
                st.session_state["music_path"])
        except Exception as e:
            st.error(f"Error loading music: {e}.")
        st.session_state["current_music"] = chosen_music

    if st.session_state["current_music"] != chosen_music:
        st.session_state["player"].stop()
        st.session_state["player"] = WinMIDIPlayer(
            st.session_state["music_path"])
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

# On Linux/macOS: render MIDI to WAV with FluidSynth, play with st.audio
elif music_extension == ".mid" and sys.platform != "win32":
    with st.spinner("Rendering MIDI to WAV..."):
        try:
            player = MIDIWavConverter(st.session_state["music_path"])
            wav_path = player.to_wav()
            st.session_state["player"] = player
            with col2:
                st.audio(wav_path)
        except Exception as e:
            st.error(f"Error rendering MIDI: {e}")

# For OGG and MP3 files, just use st.audio to play them
elif music_extension in [".ogg", ".mp3"]:
    st.session_state["player"] = None
    with col2:
        st.audio(st.session_state["music_path"])

else:
    st.error(f"Unsupported music format: {music_extension}")
