import streamlit as st

import matplotlib.pyplot as plt

textures = st.session_state["wad"].textures.keys()

ncols = 8
nrows = len(textures) // ncols + 1 if len(textures) % ncols != 0 else len(textures) // ncols

fig, ax = plt.subplots(nrows, ncols, figsize=(ncols, nrows))
ax = ax.ravel()
fig.patch.set_alpha(0)

with st.spinner(f"Drawing {len(textures)} textures..."):
    for i, texture_name in enumerate(textures):
        st.session_state["viewer"].draw_tex(texture_name, ax=ax[i])
        ax[i].axis("off")

    if len(textures) < len(ax):
        for i in range(len(textures), len(ax)):
            ax[i].axis("off")
    st.pyplot(fig, format="png", dpi=300)
