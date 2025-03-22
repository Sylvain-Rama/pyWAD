import matplotlib.pyplot as plt
import numpy as np
import argparse
import sys
import shutil
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


def draw_tex(wad, tex_name, ax=None, scaler=1):
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

    texture_data = wad.textures[tex_name]
    pix_width, pix_height = texture_data["width"], texture_data["height"]

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(pix_width / 100 * scaler, pix_height / 100 * scaler))
        ax.axis("off")
        ax.set_aspect("equal")
        output_fig = True

    pixmap = np.zeros((pix_width, pix_height), dtype=np.uint8)
    alphamap = np.zeros((pix_width, pix_height), dtype=np.uint8)

    for patch_name, x, y in texture_data["patches"]:

        idx = wad.lump_names.index(patch_name)

        _, offset, size = wad.lumps[idx]
        img, alpha, _, _ = wad._read_patch_data(offset, size)

        # x and y are flipped as the image will be transposed after
        pixmap = paste_array(pixmap, img, y, x)
        alphamap = paste_array(alphamap, alpha, y, x)

    alphamap = alphamap.T[:, :, np.newaxis] * np.ones((1, 1, 4))

    rgb_img = wad.palette[pixmap.T]

    rgba_img = rgb_img * alphamap
    ax.imshow(rgba_img / 255, interpolation="nearest", aspect=1.2)

    if output_fig:
        return fig


if __name__ == "__main__":

    args = argparse.ArgumentParser()
    args.add_argument("--wad", "-w", type=str, help="Path to WAD file", default="WADs/DOOM.wad")
    args.add_argument(
        "--command", "-c", type=str, help="Command to run", choices=["draw_map", "draw_tex"], default="draw_map"
    )
    args.add_argument("--map", "-m", type=str, help="Map name", default="E1M1")
    args.add_argument("--palette", "-p", type=str, help="Palette name", default="OMGIFOL")
    args.add_argument("--texture", "-t", type=str, help="Texture name", default="AASTINKY")

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

    elif args.command == "draw_tex":
        if args.texture == "*":
            textures_to_draw = wad.textures.keys()
        else:
            textures_to_draw = [args.texture]

        for texture_name in textures_to_draw:
            fig = draw_tex(wad, texture_name)
            fig.savefig(f"output/{texture_name}.png", bbox_inches="tight", dpi=300)
