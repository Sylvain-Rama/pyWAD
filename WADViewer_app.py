import math
import streamlit as st

from loguru import logger
from src.WADParser import WAD_file
from src.WADViewer import draw_map, draw_tex, save_music


st.set_page_config(
    page_title="pyWAD",
    page_icon="👋",
    layout="wide",
)

wad = None


with st.sidebar:
    st.header("WAD Viewer")
    page = st.radio("Go to", ["Flats", "Maps", "Musics", "Sprites", "Textures"])

    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        wad = WAD_file(uploaded_file)

if wad is None:
    st.write("Upload a WAD file to get started.")
    st.write("You can download some WAD files from the [Doom Wiki](https://doomwiki.org/wiki/Category:Doom_II_WADs).")

elif page == "Maps":

    col1, col2, col3, _ = st.columns([0.2, 0.2, 0.2, 1])
    with col1:
        chosen_map = st.selectbox("Map", wad.maps.keys())
    with col2:
        palette = st.selectbox("Palette", ["OMGIFOL", "DOOM", "HERETIC"])
    with col3:
        things = st.selectbox("Things", ["None", "Dots"])
        # show_secrets = st.checkbox("Show Secrets")
    fig = draw_map(wad.map(chosen_map), palette=palette)
    st.pyplot(fig)

elif page == "Flats":
    flats = wad.flats.keys()
    flat_list = []
    captions = []
    for flat_name in flats:
        rgb_image = wad.draw_flat(*wad.flats[flat_name]) / 255
        flat_list.append(rgb_image)
        captions.append(flat_name)

    st.image(flat_list, width=64, caption=captions, output_format="PNG")

elif page == "Textures":
    textures = wad.textures.keys()
    texture_list = []
    captions = []
    for texture_name in textures:
        rgb_image = draw_tex(wad, texture_name) / 255
        texture_list.append(rgb_image)
        captions.append(texture_name)

    st.image(texture_list, caption=captions, output_format="PNG")


elif page == "Musics":
    music_names = wad.musics.keys()
    ncols = 4
    nrows = math.ceil(len(music_names) / ncols)

    for music in music_names:
        save_music(wad, music)

    col1, col2, col3, col4 = st.columns(ncols)
    cols = [col1, col2, col3, col4]

    for i, lump_name in enumerate(music_names):

        with cols[i % ncols]:
            st.write(lump_name)

            st.audio(f"output/{lump_name}.mid", format="audio/mid")
