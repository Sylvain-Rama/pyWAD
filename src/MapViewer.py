import matplotlib.pyplot as plt
import argparse

from src.WADParser import WAD_file
from src.palettes import MAP_CMAPS


def draw_map(map_data, palette="OMGIFOL", ax=None, scaler=1, show_secret=True):
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 12))
        output_fig = True

    cmap = MAP_CMAPS[palette]

    step_color = [x / 255 for x in cmap["2-sided"]]
    for line in map_data["steps"]:
        ax.plot(line[:, 0], line[:, 1], color=step_color, linewidth=0.6)

    block_color = [x / 255 for x in cmap["block"]]
    for line in map_data["walls"]:
        ax.plot(line[:, 0], line[:, 1], color=block_color, linewidth=0.6)

    if show_secret:
        secret_color = [x / 255 for x in cmap["secret"]]
        for line in map_data["secret"]:
            ax.plot(line[:, 0], line[:, 1], color=block_color, linewidth=0.6)

    ax.axis("equal")
    ax.axis("off")

    if output_fig:
        return fig


if __name__ == "__main__":

    args = argparse.ArgumentParser()
    args.add_argument("--wad", "-w", type=str, help="Path to WAD file", default="WADs/DOOM.wad")
    args.add_argument("--map", "-m", type=str, help="Map name", default="E1M1")
    args.add_argument("--palette", "-p", type=str, help="Palette name", default="OMGIFOL")

    args = args.parse_args()
    wad = WAD_file(args.wad)

    if args.map == "*":
        maps_to_draw = wad.maps.keys()
    else:
        maps_to_draw = [args.map]

    for map_name in maps_to_draw:
        map_data = wad.map(args.map)
        fig = draw_map(map_data, palette=args.palette)
        fig.savefig(f"output/{map_name}.png")
