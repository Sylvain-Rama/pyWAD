import math
import streamlit as st
import os
from loguru import logger
import sys
import matplotlib.pyplot as plt


sys.path.append("src/")

from WADParser import WAD_file
from WADViewer import WadViewer
from mus2mid import Mus2Mid
from WADPlayer import MIDIPlayer
from palettes import MAP_CMAPS


st.set_page_config(
    page_title="pyWAD",
    page_icon="👋",
    layout="wide",
)


if "wad" not in st.session_state:
    st.session_state["wad"] = None
    st.session_state["viewer"] = None


if "player" not in st.session_state:
    st.session_state["player"] = None
    st.session_state["current_music"] = None


with st.sidebar:
    st.header("WAD Viewer")
    page = st.radio("Go to", ["Flats", "Maps", "Musics", "Sprites", "Textures"])
    if st.session_state["wad"] is None:
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            wad = WAD_file(uploaded_file)
            st.session_state["wad"] = wad
            st.session_state["viewer"] = WadViewer(wad)

if st.session_state["wad"] is None:
    st.write("Upload a WAD file to get started.")
    st.write("You can download some WAD files from the [Doom Wiki](https://doomwiki.org/wiki/Category:Doom_II_WADs).")

elif page == "Maps":

    col1, col2, col3, _ = st.columns([0.2, 0.2, 0.2, 1])
    with col1:
        chosen_map = st.selectbox("Map", st.session_state["wad"].maps.keys())
    with col2:
        palette = st.selectbox("Palette", list(MAP_CMAPS.keys()), index=1)
    with col3:
        things = st.selectbox("Things", ["None", "Dots"])
        # show_secrets = st.checkbox("Show Secrets")
    fig = st.session_state["viewer"].draw_map(chosen_map, palette=palette)
    st.pyplot(fig, use_container_width=True)

elif page == "Flats":
    flats = st.session_state["wad"].flats.keys()

    ncols = 8
    nrows = len(flats) // ncols + 1 if len(flats) % ncols != 0 else len(flats) // ncols
    fig, ax = plt.subplots(nrows, ncols, figsize=(ncols * 3, nrows * 3))
    ax = ax.ravel()

    with st.spinner(f"Drawing {len(flats)} flats..."):
        for i, flat_name in enumerate(flats):
            st.session_state["viewer"].draw_flat(flat_name, ax=ax[i])
            ax[i].set_title(flat_name)
            ax[i].axis("off")

        [ax[i].axis("off") for i in range(len(flats), len(ax))]
        st.pyplot(fig, use_container_width=True)


elif page == "Textures":
    textures = st.session_state["wad"].textures.keys()

    ncols = 6
    nrows = len(textures) // ncols + 1 if len(textures) % ncols != 0 else len(textures) // ncols
    fig, ax = plt.subplots(nrows, ncols, figsize=(ncols * 2, nrows * 2))
    ax = ax.ravel()

    with st.spinner(f"Drawing {len(textures)} textures..."):
        for i, texture_name in enumerate(textures):
            st.session_state["viewer"].draw_tex(texture_name, ax=ax[i])
            ax[i].axis("off")
            ax[i].set_title(texture_name, fontsize=10)

        [ax[i].axis("off") for i in range(len(textures), len(ax))]
        st.pyplot(fig)


elif page == "Musics":

    with st.container():
        col1, col2, col3, col4, _ = st.columns([2, 1, 1, 3, 3], vertical_alignment="bottom")

    music_names = list(st.session_state["wad"].musics.keys())

    with col1:
        chosen_music = st.selectbox("Music", music_names)
    temp_name = f"output/{chosen_music}.mus"
    midi_name = f"output/{chosen_music}.mid"

    if f"{chosen_music}.mid" not in os.listdir("output"):
        st.session_state["wad"].save_mus(chosen_music, temp_name)
        m2m = Mus2Mid(temp_name)
        m2m.to_midi(midi_name)
        os.remove(temp_name)

    # Create the player if it's not created yet or if the music is changed
    if st.session_state["player"] is None:
        st.session_state["player"] = MIDIPlayer(midi_name)
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
