# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: wildfire-composer
#     language: python
#     name: wildfire-composer
# ---

# %% [markdown]
# # Wildfires

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import pystac_client
from datetime import datetime, timedelta
from odc.stac import configure_s3_access, stac_load

from wildfire_composer.config import Config
from wildfire_composer.raster import get_data
from wildfire_composer.viz import plot_compare
from wildfire_composer.spectral import compute_nbr

# %%
cfg = Config.load("../config/config.toml")
cfg_aois = cfg.aois
cfg_stac = cfg.stac

# %%
catalog = pystac_client.Client.open(cfg_stac.url)

configure_s3_access(aws_unsigned=True)

# %% [markdown]
# ## Pyrenees

# %%
cfg_aoi = cfg_aois["pyrenees"]

(ds_pre, ds_post) = get_data(cfg_aoi, cfg_stac, catalog)

# %%
# %%time
ds_pre_pyrenees = ds_pre.compute()
ds_post_pyrenees = ds_post.compute()

# %%
import xarray as xr
ds = xr.concat([ds_pre_pyrenees, ds_post_pyrenees], dim="time")
ds = ds.assign_coords({"time": ["pre", "post"]})
ds.sel(time="pre")

# %%
ds.to_zarr("ds.zarr", mode="w")

# %%
_ds = xr.open_dataarray("ds.zarr", engine="zarr")
_ds

# %%
rgb_pre_pyrenees = _ds.sel(band=["red", "green", "blue"], time="pre")
rgb_post_pyrenees = _ds.sel(band=["red", "green", "blue"], time="post")

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "RGB Composite", rgb_pre_pyrenees, rgb_post_pyrenees)

# %%
rgb_pre_pyrenees = ds_pre_pyrenees.sel(band=["red", "green", "blue"])
rgb_post_pyrenees = ds_post_pyrenees.sel(band=["red", "green", "blue"])

false_pre_pyrenees = ds_pre_pyrenees.sel(band=["swir16", "nir", "red"])
false_post_pyrenees = ds_post_pyrenees.sel(band=["swir16", "nir", "red"])

nbr_pre_pyrenees = compute_nbr(ds_pre_pyrenees.sel(band=["nir", "swir16"]))
nbr_post_pyrenees = compute_nbr(ds_post_pyrenees.sel(band=["nir", "swir16"]))
dnbr_pyrenees = nbr_pre_pyrenees - nbr_post_pyrenees

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "RGB Composite", rgb_pre_pyrenees, rgb_post_pyrenees)

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", false_pre_pyrenees, false_post_pyrenees)

# %% [markdown]
# ## Diois

# %%
cfg_aoi = cfg_aois["diois"]

(ds_pre, ds_post) = get_data(cfg_aoi, cfg_stac, catalog)

# %%
# %%time
ds_pre_dois = ds_pre.compute()
ds_post_dois = ds_post.compute()

# %%
rgb_pre_dois = ds_pre_dois.sel(band=["red", "green", "blue"])
rgb_post_dois = ds_post_dois.sel(band=["red", "green", "blue"])

false_pre_dois = ds_pre_dois.sel(band=["swir16", "nir", "red"])
false_post_dois = ds_post_dois.sel(band=["swir16", "nir", "red"])

nbr_pre_dois = compute_nbr(ds_pre_dois.sel(band=["nir", "swir16"]))
nbr_post_dois = compute_nbr(ds_post_dois.sel(band=["nir", "swir16"]))
dnbr_dois = nbr_pre_dois - nbr_post_dois

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "RGB Composite", rgb_pre_dois, rgb_post_dois)

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", false_pre_dois, false_post_dois)

# %% [markdown]
# ## Korcula

# %%
cfg_aoi = cfg_aois["korcula"]

# %%
(ds_pre, ds_post) = get_data(cfg_aoi, cfg_stac, catalog)

# %%
# %%time
ds_pre_kolura = ds_pre.compute()
ds_post_kolura = ds_post.compute()

# %%
rgb_pre_kolura = ds_pre_kolura.sel(band=["red", "green", "blue"])
rgb_post_kolura = ds_post_kolura.sel(band=["red", "green", "blue"])

false_pre_kolura = ds_pre_kolura.sel(band=["swir16", "nir", "red"])
false_post_kolura = ds_post_kolura.sel(band=["swir16", "nir", "red"])

nbr_pre_kolura = compute_nbr(ds_pre_kolura.sel(band=["nir", "swir16"]))
nbr_post_kolura = compute_nbr(ds_post_kolura.sel(band=["nir", "swir16"]))
dnbr_kolura = nbr_pre_kolura - nbr_post_kolura

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "RGB Composite", rgb_pre_kolura, rgb_post_kolura)

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", false_pre_kolura, false_post_kolura)

# %% [markdown]
# ## Almeira

# %%
cfg_aoi = cfg_aois["almeria"]

# %%
(ds_pre, ds_post) = get_data(cfg_aoi, cfg_stac, catalog)

# %%
# %%time
ds_pre_almeira = ds_pre.compute()
ds_post_almeira = ds_post.compute()

# %%
rgb_pre_almeira = ds_pre_almeira.sel(band=["red", "green", "blue"])
rgb_post_almeira = ds_post_almeira.sel(band=["red", "green", "blue"])

false_pre_almeira = ds_pre_almeira.sel(band=["swir16", "nir", "red"])
false_post_almeira = ds_post_almeira.sel(band=["swir16", "nir", "red"])

nbr_pre_almeira = compute_nbr(ds_pre_almeira.sel(band=["nir", "swir16"]))
nbr_post_almeira = compute_nbr(ds_post_almeira.sel(band=["nir", "swir16"]))
dnbr_almeira = nbr_pre_almeira - nbr_post_almeira

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "RGB Composite", rgb_pre_almeira, rgb_post_almeira)

# %%
plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", false_pre_almeira, false_post_almeira)

# %%
_ds = xr.open_dataarray("../data/rasters/raster_EMSR892.zarr/", engine="zarr")
_ds
_ds_pre = _ds.sel(band=["swir16", "nir", "red"]).sel(time="pre")
_ds_post = _ds.sel(band=["swir16", "nir", "red"]).sel(time="post")

plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", _ds_pre, _ds_post)

# %%
/205/ /raster_EMSR890.zarr
/206/ /raster_EMSR892.zarr
/207/ /raster_EMSR896.zarr
/197/ /raster_EMSR900.zarr

# %%
_ds = xr.open_dataarray("../data/rasters/raster_EMSR890.zarr/", engine="zarr")
_ds
_ds_pre_1 = _ds.sel(band=["swir16", "nir", "red"]).sel(time="pre")
_ds_post_1 = _ds.sel(band=["swir16", "nir", "red"]).sel(time="post")

plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", _ds_pre, _ds_post)

# %%
_ds = xr.open_dataarray("../data/rasters/raster_EMSR896.zarr/", engine="zarr")
_ds
_ds_pre = _ds.sel(band=["swir16", "nir", "red"]).sel(time="pre")
_ds_post = _ds.sel(band=["swir16", "nir", "red"]).sel(time="post")

plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", _ds_pre, _ds_post)

# %%
_ds2 = xr.open_dataarray("../data/rasters/raster_EMSR889.zarr/", engine="zarr")
_ds_pre_2 = _ds2.sel(band=["swir16", "nir", "red"]).sel(time="pre")
_ds_post_2 = _ds2.sel(band=["swir16", "nir", "red"]).sel(time="post")

_ds3 = xr.open_dataarray("../data/rasters/raster_EMSR888.zarr/", engine="zarr")
_ds_pre_3 = _ds3.sel(band=["swir16", "nir", "red"]).sel(time="pre")
_ds_post_3 = _ds3.sel(band=["swir16", "nir", "red"]).sel(time="post")

# %%
fig = mosaic([_ds_post_2, _ds_post_3, _ds_post], ["ITALY\nCile", "SPAIN", "FRANCE"], ["Milan", "Madrid", "Paris"])

# %%
_ds = xr.open_dataarray("../data/rasters/raster_EMSR900.zarr/", engine="zarr")
_ds
_ds_pre = _ds.sel(band=["swir16", "nir", "red"]).sel(time="pre")
_ds_post = _ds.sel(band=["swir16", "nir", "red"]).sel(time="post")

plot_compare(cfg_aoi.region, cfg_aoi.name, "False Image (SWIR, NIR, RED)", _ds_pre, _ds_post)

# %%
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe


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

    axes = axes.flatten()

    for ax, raster, country, region in zip(axes, rasters, countries, regions):
        raster.plot.imshow(ax=ax, robust=True)
        # align tops when heights differ, remove the xarray title, ticks, labels and frame.
        ax.set_anchor("N")
        ax.set_title("")
        ax.axis("off")

        # Add centered text in the image.
        add_text(ax, country, 32, "bottom")
        add_text(ax, region, 20, "top")

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
        # path_effects=[pe.withStroke(linewidth=3.5, foreground="black")],
    )


# %%
