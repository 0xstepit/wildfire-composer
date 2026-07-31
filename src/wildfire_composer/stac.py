import datetime

import pystac_client
from odc.stac import stac_load


def catalog_search(
    cfg_stac,
    catalog: pystac_client.client.Client,
    bounding_box: tuple,
    max_cloud: float,
    ref_date: datetime.datetime,
    delta: datetime.timedelta,
    pre_fire: bool,
):
    time_order = "desc" if pre_fire else "asc"
    dates = (
        f"{(ref_date - delta).isoformat()}/{ref_date.isoformat()}"
        if pre_fire
        else f"{ref_date.isoformat()}/{(ref_date + delta).isoformat()}"
    )

    search = catalog.search(
        collections=[cfg_stac.collection],
        bbox=bounding_box,
        datetime=dates,
        query={"eo:cloud_cover": {"lt": max_cloud}},
        sortby=[
            {"field": "properties.eo:cloud_cover", "direction": "asc"},
            {"field": "properties.datetime", "direction": time_order},
        ],
    )
    return search.item_collection()


def load_from_stac(cfg_stac, items, bounding_box):
    return stac_load(
        items,
        bands=cfg_stac.bands,
        resolution=10,
        crs="utm",
        bbox=bounding_box,
        chunks={"x": cfg_stac.chunk_size, "y": cfg_stac.chunk_size},
        groupby="solar_day",
    )
