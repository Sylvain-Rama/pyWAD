import streamlit as st
import matplotlib.pyplot as plt
from loguru import logger

spritesheets = sorted(st.session_state["wad"].spritesheets.keys())

sprite_name = st.selectbox("Choose sprite", options=spritesheets)

sprite_list = st.session_state["wad"].spritesheets[sprite_name]
ncols = 5
nrows = len(sprite_list) // ncols + 1 if len(sprite_list) % ncols != 0 else len(sprite_list) // ncols
fig, ax = plt.subplots(nrows, ncols, figsize=(ncols * 0.8, nrows), dpi=150)
ax = ax.ravel()
fig.patch.set_alpha(0)


with st.spinner(f"Drawing {len(sprite_list)} sprites..."):
    for i, name in enumerate(sprite_list):

        st.session_state["viewer"].draw_patch(name, ax=ax[i])
        ax[i].axis("off")
        ax[i].patch.set_alpha(0)

    if len(sprite_list) < len(ax):
        for i in range(len(sprite_list), len(ax)):
            ax[i].axis("off")
    st.pyplot(fig, use_container_width=True, format="png", dpi=300)
