"""Command-line interface for the wildfire composer."""

import os

import typer
from rich.console import Console

from wildfire_composer import fetch
from wildfire_composer.config import Config
from wildfire_composer.db import connect, list_wildfires

DEFAULT_DB = os.environ.get("CEMS_DB", "data/cems.duckdb")
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
):

    con = connect(db_path)
    rows = list_wildfires(con, 10)
    con.close()
    if not rows:
        raise typer.Exit()
    console.print(rows)


if __name__ == "__main__":
    app()
