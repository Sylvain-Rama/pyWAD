import streamlit as st
from src.palettes import MAP_CMAPS


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
