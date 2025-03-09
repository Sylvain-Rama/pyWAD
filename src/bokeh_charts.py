import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from bokeh.plotting import figure, save
from bokeh.io import output_file


def use_file_for_bokeh(chart: figure, chart_height=500):
    output_file("bokeh_graph.html")
    save(chart)
    with open("bokeh_graph.html", "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=chart_height)


st.bokeh_chart = use_file_for_bokeh
df = pd.DataFrame({"x": [0, 1, 2, 3, 4, 5, 6], "y": [2, 6, 4, 6, 8, 3, 5]})

st.dataframe(df)

p = figure(x_axis_label="x", y_axis_label="y")
p.line(df.x, df.y)
st.bokeh_chart(p)
