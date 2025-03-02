import streamlit as st
from src.WADParser import WAD_file


uploaded_file = st.file_uploader("Choose a file")
if uploaded_file is not None:
    wad = WAD_file(uploaded_file)
    st.write(wad.lump_names)
