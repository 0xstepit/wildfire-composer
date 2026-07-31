"""Utility submodule for the visualization of raster images."""

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np


def plot_compare(location, region, title, ds_pre, ds_post):
    fig, ax = plt.subplots(ncols=2, figsize=(30, 15, "cm"))
    fig.suptitle(
        f"{location.title()}, {region.title()} {title}", fontsize=16, fontweight="bold"
    )

    ds_pre.plot.imshow(ax=ax[0], robust=True)
    ds_post.plot.imshow(ax=ax[1], robust=True)

    ax[0].set_aspect("equal")
    ax[1].set_aspect("equal")
    ax[0].set_title("Pre Fire")
    ax[1].set_title("Post Fire")
    ax[0].tick_params(axis="x", rotation=45)
    ax[1].tick_params(axis="x", rotation=45)


def mosaic(
    rasters,
    countries,
    regions,
    ncols=None,
    figsize=None,
    panel=4.5,
    gap=0.025,
    facecolor="black",
):
    n = len(rasters)
    if ncols is None:
        ncols = n if n <= 3 else 2
    nrows = int(np.ceil(n / ncols))
    if figsize is None:
        figsize = (panel * ncols, panel * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, facecolor=facecolor)
    axes = np.atleast_1d(axes).ravel()

    for ax, raster, country, region in zip(axes, rasters, countries, regions):
        raster.plot.imshow(ax=ax, robust=True)
        # align tops when heights differ, remove the xarray title, ticks, labels and frame.
        ax.set_anchor("N")
        ax.set_title("")
        ax.axis("off")

        # Add centered text in the image. Yes, bottom place the text on top and top on the bottom...
        add_text(ax, country, 24, "bottom")
        add_text(ax, region, 12, "top")

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=gap, hspace=gap)

    return fig


def add_text(ax, text: str, size: int, vertical_position: str):
    ax.text(
        0.5,
        0.5,
        text,
        transform=ax.transAxes,
        ha="center",
        va=vertical_position,
        color="white",
        fontsize=size,
        family="monospace",
        fontweight="bold",
        path_effects=[pe.withStroke(linewidth=1.5, foreground="black")],
    )
