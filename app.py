import streamlit as st
import os
from loguru import logger
import sys
import matplotlib.pyplot as plt


sys.path.append("src/")

from WADParser import WAD_file
from WADViewer import WadViewer
from app_utils import banner_html


def get_titlepic(viewer):
    fig, ax = plt.subplots(1, 1, figsize=(1.6, 1))
    fig.patch.set_alpha(0)
    ax.axis("off")

    if "TITLEPIC" in viewer.wad.lump_names:
        viewer.draw_patch("TITLEPIC", ax=ax)
    elif "TITLE" in viewer.wad.lump_names:
        viewer.draw_flat("TITLE", ax=ax)
    else:
        return None

    return fig


def init_app():
    if "wad" not in st.session_state:
        st.session_state["wad"] = None
        st.session_state["viewer"] = None
        st.session_state["wad_path"] = None
        st.session_state["title_pic"] = None


st.set_page_config(page_title="WAD Viewer", page_icon="media/skull.png", layout="centered")
st.components.v1.html(banner_html)


init_app()
st.header("WAD Viewer")


head_container = st.container(border=False, height=300)
with head_container:
    head_col1, head_col2 = st.columns([1, 1])
with head_col1:
    uploaded_file = st.file_uploader("Choose a file", accept_multiple_files=False)

if uploaded_file is not None:
    if uploaded_file.name != st.session_state["wad_path"]:
        wad = WAD_file(uploaded_file)
        st.session_state["wad"] = wad
        st.session_state["wad_path"] = uploaded_file.name
        st.session_state["viewer"] = WadViewer(wad)
        st.session_state["title_pic"] = get_titlepic(st.session_state["viewer"])

        # Cleaning the output folder.
        for f in os.listdir("output"):
            if f != ".gitkeep":
                os.remove(os.path.join("output", f))


if st.session_state["title_pic"] is not None:
    with head_col2:
        st.pyplot(st.session_state["title_pic"], format="png", dpi=300, bbox_inches="tight", use_container_width=True)

if st.session_state["wad"] is None:
    st.write("Upload a WAD file to get started.")
    st.write("You can download some WAD files from the [Doom Wiki](https://doomwiki.org/wiki/Category:Doom_II_WADs).")
    st.write("The full version of the app is available on [Github](https://github.com/Sylvain-Rama/pyWAD) ")

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
    if st.session_state["wad"].spritesheets is not None:
        pages.append(st.Page("st_pages/sprites.py", title="Sprites"))
    if st.session_state["wad"].sounds is not None:
        pages.append(st.Page("st_pages/sounds.py", title="Sounds"))
    pg = st.navigation(pages)

    pg.run()
