import streamlit as st
from src.palettes import MAP_CMAPS
from loguru import logger


col1, col2, col3, col4 = st.columns(4)
with col1:
    chosen_map = st.selectbox("Map", options=sorted(st.session_state["wad"].maps.keys()))
with col2:
    palette = st.selectbox("Palette", list(MAP_CMAPS.keys()), index=1)
with col3:
    things = st.selectbox("Things", ["None", "Dots"])
    show_things = things == "Dots"
with col4:
    show_secrets = st.checkbox("Show Secrets")
    show_specials = st.checkbox("Show Special", value=True)

fig = st.session_state["viewer"].draw_map(
    chosen_map, palette=palette, show_secrets=show_secrets, show_specials=show_specials, show_things=show_things
)
st.pyplot(fig, use_container_width=True, format="png", dpi=300)
