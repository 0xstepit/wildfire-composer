"""Command-line interface for the wildfire composer."""

import os
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

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
    limit: int = typer.Option(10, "--limit", help="Maximum number of returned events"),
    only_closed: Annotated[
        bool,
        typer.Option(
            "--closed/--all", help="Filter only closed or also open activations"
        ),
    ] = True,
):
    print(only_closed)

    con = connect(db_path)
    rows = list_wildfires(con, limit, only_closed)
    con.close()
    if not rows:
        raise typer.Exit()
    console.print(_wildfire_list_to_table(rows))


def _wildfire_list_to_table(rows) -> Table:
    table = Table(title="CEMS wildfire activations")
    table.add_column("Code", style="bold cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Region")
    table.add_column("Acrivated", no_wrap=True)
    table.add_column("Status", no_wrap=True)

    for row in rows:
        (code, name, countries, activation_time, closed, _, _) = row
        table.add_row(
            code,
            name,
            countries,
            activation_time,
            "[blue] closed" if closed else "[yellow] open",
        )

    return table


if __name__ == "__main__":
    app()
