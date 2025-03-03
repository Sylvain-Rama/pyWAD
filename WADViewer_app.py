import streamlit as st
from src.WADParser import WAD_file
from src.MapViewer import draw_map


st.set_page_config(
    page_title="pyWAD",
    page_icon="👋",
    layout="wide",
)

wad = None


with st.sidebar:
    st.header("WAD Viewer")
    page = st.radio("Go to", ["Flats", "Maps", "Sprites"])

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
        show_things = st.checkbox("Show Things")
        show_secrets = st.checkbox("Show Secrets")
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
