import matplotlib.pyplot as plt
import argparse
import sys
from loguru import logger

sys.path.append("src/")

from WADParser import WAD_file, open_wad_file
from palettes import MAP_CMAPS


def draw_map(map_data, palette="OMGIFOL", ax=None, scaler=1, show_secret=True):
    if ax is None:
        width, height = map_data["metadata"]["map_size"]
        wh_ratio = width / height

        fig, ax = plt.subplots(figsize=(12, 12 / wh_ratio))
        output_fig = True

    cmap = MAP_CMAPS[palette]

    bckgrd_color = [x / 255 for x in cmap["background"]]
    ax.set_facecolor(bckgrd_color)

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

    logger.info(f'Plotted map {map_data["metadata"]["map_name"]}.')

    if output_fig:
        fig.tight_layout(pad=0.2)
        return fig


def draw_tex(wad, tex_name):
    def paste_array(original, paste, x, y):
        """
        Pastes a 2D numpy array into another 2D numpy array at the specified (x, y) position.
        Allows for negative x and y values.
        I miss Labview paste-and-forget function :'(
        """
        orig_h, orig_w = original.shape
        paste_h, paste_w = paste.shape

        # Valid region in the original array
        x_start = max(x, 0)
        y_start = max(y, 0)
        x_end = min(x + paste_w, orig_w)
        y_end = min(y + paste_h, orig_h)

        # Corresponding region in the paste array
        paste_x_start = max(-x, 0)
        paste_y_start = max(-y, 0)
        paste_x_end = paste_x_start + (x_end - x_start)
        paste_y_end = paste_y_start + (y_end - y_start)

        original[y_start:y_end, x_start:x_end] = paste[paste_y_start:paste_y_end, paste_x_start:paste_x_end]

        return original

    return


if __name__ == "__main__":

    args = argparse.ArgumentParser()
    args.add_argument("--wad", "-w", type=str, help="Path to WAD file", default="WADs/DOOM.wad")
    args.add_argument(
        "--command", type=str, help="Command to run", choices=["draw_map", "draw_tex"], default="draw_map"
    )
    args.add_argument("--map", "-m", type=str, help="Map name", default="E1M1")
    args.add_argument("--palette", "-p", type=str, help="Palette name", default="OMGIFOL")

    args = args.parse_args()
    wad = open_wad_file(args.wad)

    if args.command == "draw_map":
        if args.map == "*":
            maps_to_draw = wad.maps.keys()
        else:
            maps_to_draw = [args.map]

        for map_name in maps_to_draw:
            map_data = wad.map(map_name)
            fig = draw_map(map_data, palette=args.palette)
            fig.savefig(f"output/{map_name}.png", bbox_inches="tight", dpi=300)
