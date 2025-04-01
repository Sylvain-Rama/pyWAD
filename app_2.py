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
    st.session_state["wad_path"] = None


st.header("WAD Viewer")


uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
    if uploaded_file.name != st.session_state["wad_path"]:
        wad = WAD_file(uploaded_file)
        st.session_state["wad"] = wad
        st.session_state["wad_path"] = uploaded_file.name
        st.session_state["viewer"] = WadViewer(wad)

if st.session_state["wad"] is None:
    st.write("Upload a WAD file to get started.")
    st.write("You can download some WAD files from the [Doom Wiki](https://doomwiki.org/wiki/Category:Doom_II_WADs).")

else:
    pages = []
    if st.session_state["wad"].maps is not None:
        pages.append(st.Page("pages/maps.py", title="Maps"))
    if st.session_state["wad"].flats is not None:
        pages.append(st.Page("pages/flats.py", title="Flats"))
    if st.session_state["wad"].musics is not None:
        pages.append(st.Page("pages/musics.py", title="Musics"))
    if st.session_state["wad"].textures is not None:
        pages.append(st.Page("pages/textures.py", title="Textures"))
    pg = st.navigation(pages)

    pg.run()
