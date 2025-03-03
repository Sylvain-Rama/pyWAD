import streamlit as st
from src.WADParser import WAD_file
from src.MapViewer import draw_map


st.set_page_config(
    page_title="pyWAD",
    page_icon="👋",
    layout="wide",
)

with st.sidebar:
    st.header("WAD Viewer")
    page = st.radio("Go to", ["View Lumps", "Maps"])

    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        wad = WAD_file(uploaded_file)

if page == "View Lumps":
    if wad is not None:
        st.write(wad.lump_names)

elif page == "Maps":
    if wad is not None:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            chosen_map = st.selectbox("Select a map", wad.maps.keys())
        with col2:
            palette = st.selectbox("Select a palette", ["DOOM", "OMGIFOL", "HERETIC"])
        fig = draw_map(wad.map(chosen_map), palette=palette)
        st.pyplot(fig)
