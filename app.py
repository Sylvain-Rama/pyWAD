import streamlit as st
import os
from loguru import logger
import sys
import matplotlib.pyplot as plt


sys.path.append("src/")

from WADParser import WAD_file
from WADViewer import WadViewer


def get_titlepic(wad_file, viewer):
    idx = wad_file.lump_names.index("TITLEPIC")
    _, offset, size = wad_file.lumps[idx]
    rgb = viewer.draw_patch(offset, size)

    return rgb


st.set_page_config(
    page_title="pyWAD",
    page_icon="👋",
    layout="wide",
)


if "wad" not in st.session_state:
    st.session_state["wad"] = None
    st.session_state["viewer"] = None
    st.session_state["wad_path"] = None
    st.session_state["title_pic"] = None


st.header("WAD Viewer")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
    if uploaded_file.name != st.session_state["wad_path"]:
        wad = WAD_file(uploaded_file)
        st.session_state["wad"] = wad
        st.session_state["wad_path"] = uploaded_file.name
        st.session_state["viewer"] = WadViewer(wad)
        st.session_state["title_pic"] = None

        # Cleaning the output folder.
        for f in os.listdir("output"):
            os.remove(os.path.join("output", f))

        if "TITLEPIC" in st.session_state["wad"].lump_names:
            rgb = get_titlepic(st.session_state["wad"], st.session_state["viewer"])
            height, width = rgb.shape[:2]
            st.session_state["title_pic"] = {"img": rgb / 255, "width": width}

if st.session_state["title_pic"] is not None:
    with col2:
        st.image(st.session_state["title_pic"]["img"], width=st.session_state["title_pic"]["width"])

if st.session_state["wad"] is None:
    st.write("Upload a WAD file to get started.")
    st.write("You can download some WAD files from the [Doom Wiki](https://doomwiki.org/wiki/Category:Doom_II_WADs).")

else:
    pages = []
    if st.session_state["wad"].maps is not None:
        pages.append(st.Page("st_pages/maps.py", title="Maps"))
    if st.session_state["wad"].flats is not None:
        pages.append(st.Page("st_pages/flats.py", title="Flats"))
    if st.session_state["wad"].musics is not None:
        pages.append(st.Page("st_pages/musics.py", title="Musics"))
    if st.session_state["wad"].textures is not None:
        pages.append(st.Page("st_pages/textures.py", title="Textures"))
    pg = st.navigation(pages)

    pg.run()
