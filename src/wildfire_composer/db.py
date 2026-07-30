from pathlib import Path

import duckdb

# Query to create or replace the activations table from
# the CEMS Mapping data API response to the list of activation:
# https://mapping.emergency.copernicus.eu/activations/api/activations/
LOAD_SQL = """
CREATE OR REPLACE TABLE activations AS
SELECT
    code,
    name,
    concat_ws(', ', list_transform(countries, lambda c : c.short_name)) AS countries,
    category.name AS category,
    category.slug AS category_slug,
    strftime(activationTime::TIMESTAMP, '%Y-%m-%d') AS activation_time,
    centroid AS centroid_wkt,
    ST_X(ST_GeomFromText(centroid)) AS lon,
    ST_Y(ST_GeomFromText(centroid)) AS lat,
    closed,
FROM read_json_auto('{path}', format='array')
"""

# Counts the number of activations in the database.
COUNT_ACTIVATIONS = """SELECT count(*) FROM activations"""


LIST_WILDFIRES = """
SELECT code, name, countries, activation_time, closed, lon, lat
FROM activations
WHERE (category ILIKE '%wildfire%' OR category_slug ILIKE '%fire%')
"""


def connect(db_filepath: str) -> duckdb.DuckDBPyConnection:
    """Returns a connect to a DuckDB instance at the specified path. The parent folders of the
    file are created if they don't exist.

    Parameters
    ----------
    db_filepath : str
        The filepath of the database file.

    Returns
    -------
    duckdb.DuckDBPyConnection

    """
    _create_folder_if_missing(db_filepath)

    con = duckdb.connect(db_filepath)
    con.install_extension("spatial")
    con.load_extension("spatial")

    return con


def list_wildfires(
    con: duckdb.DuckDBPyConnection,
    limit: int | None = None,
    only_closed: bool | None = None,
) -> list[tuple]:
    """Returns a possibly limited list of wildfires from the database.

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
        A duckDB connection to the CEMS database.
    limit : int | None
        Maximum number of entries to return.
    only_closed: bool | None
        Consider only closed reports in the returned list.

    Returns
    -------
    list[tuple]

    """
    query = LIST_WILDFIRES
    if only_closed:
        query += "AND closed\n"
    query += "ORDER BY activation_time DESC\n"
    if limit:
        query += f"LIMIT {int(limit)}\n"
    return con.execute(query).fetchall()


def _create_folder_if_missing(filepath: str):
    """Create the file parent folders if they don't exist.

    Parameters
    ----------
    filepath : str
        The filepath of a local file.

    """
    db_dir = Path(filepath).parent
    db_dir.mkdir(parents=True, exist_ok=True)
