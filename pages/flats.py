import streamlit as st
import matplotlib.pyplot as plt

flats = st.session_state["wad"].flats.keys()

ncols = 8
nrows = len(flats) // ncols + 1 if len(flats) % ncols != 0 else len(flats) // ncols
fig, ax = plt.subplots(nrows, ncols, figsize=(ncols, nrows))
ax = ax.ravel()

with st.spinner(f"Drawing {len(flats)} flats..."):
    for i, flat_name in enumerate(flats):
        st.session_state["viewer"].draw_flat(flat_name, ax=ax[i])
        ax[i].axis("off")

    if len(flats) < len(ax):
        for i in range(len(flats), len(ax)):
            ax[i].axis("off")
    st.pyplot(fig, use_container_width=True)
