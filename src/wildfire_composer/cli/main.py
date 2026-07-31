"""Command-line interface for the wildfire composer."""

import os
from csv import Error
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from wildfire_composer import fetch
from wildfire_composer.cems import Product, ProductStatusCode, ProductType
from wildfire_composer.cli.utils import wildfire_list_to_table
from wildfire_composer.config import Config
from wildfire_composer.db import connect, list_wildfires
from wildfire_composer.raster import Aoi, Range, fetch_and_store_data

# Create an IO file
DEFAULT_DB = os.environ.get("CEMS_DB", "data/cems.duckdb")
DEFAULT_IMG_OUT = os.environ.get("IMG_OUT", "data/images")
DEFAULT_RASTER_OUT = os.environ.get("RASTER_OUT", "data/rasters")
DEFAULT_CONFIG = os.environ.get("CONFIG", "config/config.toml")


app = typer.Typer(
    name="wildfire-composer",
    help="Genereate a wildfire composite image from the CEMS activation reports and Sentinel-2 L2A data",
    no_args_is_help=True,
)

console = Console()


@app.command()
def refresh(
    db_path: str = typer.Option(DEFAULT_DB, "--db", help="DuckDB file path"),
    cfg_path: str = typer.Option(DEFAULT_CONFIG, "--config", help="TOML configuration"),
):
    cfg = Config.load(cfg_path)
    with console.status("Fetching activations from CEMS database"):
        n = fetch.refresh(cfg.cems.url, db_path)
    console.print(f"[green]Stored {n} activations")


@app.command("list")
def list_cmd(
    db_path: str = typer.Option(DEFAULT_DB, "--db", help="DuckDB file path"),
    limit: int = typer.Option(10, "--limit", help="Maximum number of returned events"),
    include_active: Annotated[
        bool,
        typer.Option(
            "--include-active/--not-include-acrive",
            help="Filter only closed or also open activations",
        ),
    ] = False,
):
    print(include_active)

    con = connect(db_path)
    rows = list_wildfires(con, limit, include_active)
    con.close()
    if not rows:
        raise typer.Exit()
    console.print(wildfire_list_to_table(rows))


@app.command()
def render(
    codes: list[str] = typer.Argument(
        ..., help="List of one or more CEMS activation codes to render, e.g. [EMSR333]"
    ),
    cfg_path: str = typer.Option(DEFAULT_CONFIG, "--config", help="TOML configuration"),
    kind: str = typer.Option("all", "--kind", help="rgb | false-color | dnbr | all"),
    img_dir: str = typer.Option(
        DEFAULT_IMG_OUT, "--img-out", help="Output image directoriy"
    ),
    raster_dir: str = typer.Option(
        DEFAULT_RASTER_OUT, "--raster-out", help="Output raster directoriy"
    ),
):
    """
    Fetch data associated with the provided CEMS reports, create a pre and post wildfire
    rasters, and generate the raster images.
    """
    cfg = Config.load(cfg_path)

    failed: dict = {}
    # Iterate over all the CEMS code to generate rasters and images.

    raster_out = Path(raster_dir)
    raster_out.mkdir(parents=True, exist_ok=True)

    for code in codes:
        try:
            with console.status(f"Working on the raster for activation {code}"):
                raster_filepath = raster_out / f"raster_{code}"
                if not raster_filepath.with_suffix(".zarr").exists():
                    console.print("[white]Fetching extended CEMS report")
                    (aoi, start_date, end_date) = get_activation_info(cfg, code)

                    console.print("[white]Composing Sentinel-2 data")
                    fetch_and_store_data(
                        cfg_stac=cfg.stac,
                        out_file=raster_filepath,
                        aoi=aoi,
                        start_date=datetime.fromisoformat(start_date),
                        end_date=datetime.fromisoformat(end_date),
                    )
                else:
                    console.print(
                        f"[green]Raster data for activation {code} already exists at {raster_filepath}"
                    )

        except Exception as e:
            failed[code] = e

    if failed:
        for code, err in failed.items():
            console.print(f"[red]{code}: {err}")
        raise typer.Exit(1)


def get_activation_info(cfg, code):
    act = fetch.fetch_extended_activaton(cfg.cems.url_extended, code)

    name = act["name"]
    countries = ", ".join([country["name"] for country in act["countries"]])
    start_date = act["eventTime"]

    product = get_activation_aoi_product(act)
    evaluate_product_validity(product)

    aoi = Aoi(name=product.name, countries=countries, extent=product.extent)
    return aoi, start_date, product.delivery_time


def evaluate_product_validity(product: Product):
    if product.status != ProductStatusCode.F.name:
        raise Error(f"Product type is not {ProductStatusCode.F.value}")


# NOTE: we always assume that only the first AOI is used
def get_activation_aoi_product(act: dict) -> Product:
    if len(act["aois"]) != 1:
        raise Error(
            "Sorry but the tool does not support activations with more than 1 AOI"
        )

    aoi = act["aois"][0]
    aoi_product: dict = {}
    for product in aoi["products"]:
        if product["type"] == ProductType.GRA.name:
            aoi_product = product
            break
    if not aoi_product:
        raise Error(f"{ProductType.GRA.value} not found")

    return Product(
        type=aoi_product["type"],
        status=aoi_product["version"]["statusCode"],
        name=aoi_product["aoiName"],
        extent=aoi_product["extent"],
        delivery_time=aoi_product["version"]["deliveryTime"],
    )


if __name__ == "__main__":
    app()
