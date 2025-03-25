import math
import streamlit as st
import os
from loguru import logger
from src.WADParser import WAD_file
from src.WADViewer import draw_map, draw_tex, save_music
from src.WADPlayer import MIDIPlayer
from src.palettes import MAP_CMAPS


st.set_page_config(
    page_title="pyWAD",
    page_icon="👋",
    layout="wide",
)


if "wad" not in st.session_state:
    st.session_state["wad"] = None


if "player" not in st.session_state:
    st.session_state["player"] = None
    st.session_state["current_music"] = None


with st.sidebar:
    st.header("WAD Viewer")
    page = st.radio("Go to", ["Flats", "Maps", "Musics", "Sprites", "Textures"])
    if st.session_state["wad"] is None:
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            st.session_state["wad"] = WAD_file(uploaded_file)

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
    fig = draw_map(st.session_state["wad"].map(chosen_map), palette=palette)
    st.pyplot(fig)

elif page == "Flats":
    flats = st.session_state["wad"].flats.keys()
    flat_list = []
    captions = []
    for flat_name in flats:
        rgb_image = st.session_state["wad"].draw_flat(*st.session_state["wad"].flats[flat_name]) / 255
        flat_list.append(rgb_image)
        captions.append(flat_name)

    st.image(flat_list, width=64, caption=captions, output_format="PNG")

elif page == "Textures":
    textures = st.session_state["wad"].textures.keys()
    texture_list = []
    captions = []
    with st.spinner("Drawing textures..."):
        for texture_name in textures:
            rgb_image = draw_tex(st.session_state["wad"], texture_name) / 255
            texture_list.append(rgb_image)
            captions.append(texture_name)

    st.image(texture_list, caption=captions, output_format="PNG")


elif page == "Musics":
    music_names = list(st.session_state["wad"].musics.keys())

    chosen_music = st.selectbox("Music", music_names)

    if f"{chosen_music}.mid" not in os.listdir("output"):
        save_music(st.session_state["wad"], chosen_music)

    # Create the player if it's not created yet or if the music is changed
    # to do: check if playing, if yes stop.
    if st.session_state["player"] is None:
        st.session_state["player"] = MIDIPlayer(f"output/{chosen_music}.mid")
        st.session_state["current_music"] = chosen_music

    if st.session_state["current_music"] != chosen_music:
        st.session_state["player"].stop()
        st.session_state["player"] = MIDIPlayer(f"output/{chosen_music}.mid")
        st.session_state["current_music"] = chosen_music

    play_button = st.button("Play")
    if play_button:
        if st.session_state["player"] is not None:
            st.session_state["player"].play()
            st.write(f"Playing {chosen_music}...")

    stop_button = st.button("Stop")
    if stop_button:
        if st.session_state["player"] is not None:
            st.session_state["player"].stop()
