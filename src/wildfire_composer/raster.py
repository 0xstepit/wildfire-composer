from csv import Error
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import pystac_client
import xarray as xr
from odc.stac import configure_s3_access
from shapely import from_wkt

from wildfire_composer.config import StacConfig
from wildfire_composer.stac import catalog_search, load_from_stac


@dataclass(frozen=True)
class Aoi:
    name: str
    countries: str
    extent: str


class CompositeKind(Enum):
    ALL = "ALL"
    FALSE = "FALSE"
    RGB = "RGB"
    DNBR = "DNBR"


# False bands could be provided as input
FALSE_BANDS = ["swir16", "nir", "red"]
RGB_BANDS = ["red", "green", "blue"]


def mask_scl_noise(ds, bands):
    scl_mask = ds["scl"].isin([0, 1, 2, 3, 7, 8, 9, 10])
    reflectance_bands = [band for band in bands if band != "scl"]
    ds = ds[reflectance_bands].where(~scl_mask)
    ds = ds.where(ds != 0)
    return ds


# TODO: this should get the values from the metadata.
def rescale_reflectance(ds):
    return ds * 0.0001 - 0.1


def create_composite(cfg_stac, items, bounding_box):
    da = load_from_stac(cfg_stac, items, bounding_box)
    da = mask_scl_noise(da, cfg_stac.bands)
    da = rescale_reflectance(da)
    return da.mean(dim="time").to_array("band")


def get_rasters(data_filepath: Path, kind: CompositeKind):
    da = xr.open_dataarray(data_filepath.with_suffix(".zarr"), engine="zarr")
    return get_raster_by_kind(da, kind)


def get_raster_by_kind(da, kind: CompositeKind):
    if kind is CompositeKind.FALSE:
        da_pre = da.sel(band=FALSE_BANDS, time="pre")
        da_post = da.sel(band=FALSE_BANDS, time="post")
    elif kind == CompositeKind.RGB:
        da_pre = da.sel(band=RGB_BANDS, time="pre")
        da_post = da.sel(band=RGB_BANDS, time="post")
    else:
        raise Error(f"Composite kind {kind.value} is not supported yet")

    return (da_pre, da_post)


def fetch_and_store_data(
    cfg_stac: StacConfig,
    out_file: Path,
    aoi: Aoi,
    start_date: datetime,
    end_date: datetime,
):
    catalog = pystac_client.Client.open(cfg_stac.url)
    configure_s3_access(aws_unsigned=True)

    bbox = from_wkt(aoi.extent).bounds

    _start_date = start_date - timedelta(
        days=1
    )  # 1 day before start date just to be sure

    # TODO: move cloud and delta to config
    max_cloud_cover = 20

    items_pre = catalog_search(
        cfg_stac, catalog, bbox, max_cloud_cover, _start_date, timedelta(days=15), True
    )
    items_post = catalog_search(
        cfg_stac, catalog, bbox, max_cloud_cover, end_date, timedelta(days=30), False
    )

    if len(items_pre) == 0:
        raise Error("No PRE fire scenes found")

    if len(items_post) == 0:
        raise Error("No POST fire scenes found")

    da_pre = create_composite(cfg_stac, items_pre, bbox).compute()
    da_post = create_composite(cfg_stac, items_post, bbox).compute()

    # Store the pre and post composite along a time dimension.
    da = xr.concat([da_pre, da_post], dim="time")
    da = da.assign_coords({"time": ["pre", "post"]})

    da.to_zarr(f"{out_file}.zarr", mode="w")
