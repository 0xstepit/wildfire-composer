from csv import Error
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pystac_client
import xarray as xr
from odc.stac import configure_s3_access
from shapely import from_wkt

from wildfire_composer.config import StacConfig
from wildfire_composer.stac import catalog_search, load_stac_ds

km2deg = 1 / 111


@dataclass(frozen=True)
class Aoi:
    name: str
    countries: str
    extent: str


@dataclass()
class Range:
    start: date
    end: date

    @property
    def as_str(self):
        return f"{self.start.isoformat()}/{self.end.isoformat()}"


def mask_scl_noise(ds, bands):
    scl_mask = ds["scl"].isin([0, 1, 2, 3, 7, 8, 9, 10])
    reflectance_bands = [band for band in bands if band != "scl"]
    ds = ds[reflectance_bands].where(~scl_mask)
    ds = ds.where(ds != 0)
    return ds


def rescale_reflectance(ds):
    return ds * 0.0001 - 0.1


def create_composite(items, cfg_stac, bounding_box):
    ds = load_stac_ds(cfg_stac, items, bounding_box)
    ds = mask_scl_noise(ds, cfg_stac.bands)
    ds = rescale_reflectance(ds)
    return ds.mean(dim="time").to_array("band")


# For the end day we can just qeury all the scenes after the start for 1 month, with a nice filter for cloud
# if the fire is still active we will not get the scenes.
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

    delta = timedelta(days=15)

    items_pre = catalog_search(cfg_stac, catalog, bbox, 20, _start_date, delta, True)
    items_post = catalog_search(cfg_stac, catalog, bbox, 20, end_date, delta, False)

    if len(items_pre) == 0:
        raise Error("No PRE fire scenes found")

    if len(items_post) == 0:
        raise Error("No POST fire scenes found")

    ds_pre = create_composite(items_pre, cfg_stac, bbox).compute()
    ds_post = create_composite(items_post, cfg_stac, bbox).compute()

    ds = xr.concat([ds_pre, ds_post], dim="time")
    ds = ds.assign_coords({"time": ["pre", "post"]})

    ds.to_zarr(f"{out_file}.zarr", mode="w")


def get_data(cfg_aoi, cfg_stac, catalog):
    edge = cfg_aoi.edge / 1000 * km2deg / 2
    lat, lon = cfg_aoi.lat, cfg_aoi.lon
    bounding_box = (lon - edge, lat - edge, lon + edge, lat + edge)

    start_date = datetime.strptime(cfg_aoi.start, "%Y-%m-%d") - timedelta(
        days=1
    )  # 1 day before start date
    end_date = datetime.strptime(cfg_aoi.end, "%Y-%m-%d") + timedelta(
        days=1
    )  # 1 day after end date
    delta = timedelta(cfg_aoi.time_buffer_days)

    items_pre = catalog_search(
        cfg_stac,
        catalog,
        bounding_box,
        cfg_aoi.max_cloud_coverage,
        start_date,
        delta,
        True,
    )
    items_post = catalog_search(
        cfg_stac,
        catalog,
        bounding_box,
        cfg_aoi.max_cloud_coverage,
        end_date,
        delta,
        False,
    )

    assert len(items_pre) != 0, "No pre wildfire items"
    assert len(items_post) != 0, "No post wildfire items"

    ds_pre = create_composite(items_pre, cfg_stac, bounding_box)
    ds_post = create_composite(items_post, cfg_stac, bounding_box)

    return (ds_pre, ds_post)
