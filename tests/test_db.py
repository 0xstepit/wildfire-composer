"""Tests for `wildfire_composer.db`.

These tests exercise a real (file-backed) DuckDB instance. The first run needs the
`spatial` extension, which DuckDB downloads once and then caches locally.
"""

import json

import pytest

from wildfire_composer.db import (
    COUNT_ACTIVATIONS,
    LOAD_SQL,
    _create_folder_if_missing,
    connect,
    list_wildfires,
)

pytestmark = pytest.mark.network


ACTIVATIONS = [
    {
        "code": "EMSR001",
        "name": "Closed wildfire, Italy",
        "countries": ["Italy"],
        "category": "Wildfire",
        "activationTime": "2024-07-01T10:00:00",
        "centroid": "POINT (9.5 40.5)",
        "closed": True,
    },
    {
        "code": "EMSR002",
        "name": "Older closed wildfire",
        "countries": ["France", "Spain"],
        "category": "Forest fire / Wildfire",
        "activationTime": "2023-06-15T10:00:00",
        "centroid": "POINT (2.0 43.0)",
        "closed": True,
    },
    {
        "code": "EMSR003",
        "name": "Open wildfire",
        "countries": ["Greece"],
        "category": "WILDFIRE",
        "activationTime": "2025-08-20T10:00:00",
        "centroid": "POINT (23.7 37.9)",
        "closed": False,
    },
    {
        "code": "EMSR004",
        "name": "A flood",
        "countries": ["Portugal"],
        "category": "Flood",
        "activationTime": "2025-01-05T10:00:00",
        "centroid": "POINT (-9.1 38.7)",
        "closed": True,
    },
]


@pytest.fixture
def con(tmp_path):
    """A connection to a throwaway database preloaded with the sample activations."""
    source = tmp_path / "activations.json"
    source.write_text(json.dumps(ACTIVATIONS))

    connection = connect(str(tmp_path / "db" / "cems.duckdb"))
    connection.execute(LOAD_SQL.format(path=source.as_posix()))
    yield connection
    connection.close()


def test_connect_creates_missing_parent_folders(tmp_path):
    """`connect` creates the parent directories of the database file."""
    db_path = tmp_path / "deeply" / "nested" / "cems.duckdb"

    connection = connect(str(db_path))
    connection.close()

    assert db_path.exists()


def test_connect_loads_the_spatial_extension(tmp_path):
    """The spatial functions used by `LOAD_SQL` are available on the connection."""
    connection = connect(str(tmp_path / "cems.duckdb"))
    try:
        (lon,) = connection.execute(
            "SELECT ST_X(ST_GeomFromText('POINT (9.5 40.5)'))"
        ).fetchone()
    finally:
        connection.close()

    assert lon == pytest.approx(9.5)


def test_load_sql_populates_the_activations_table(con):
    """Every record of the JSON payload lands in the `activations` table."""
    (count,) = con.execute(COUNT_ACTIVATIONS).fetchone()

    assert count == len(ACTIVATIONS)


def test_load_sql_flattens_countries_and_splits_the_centroid(con):
    """Countries are joined into a string and the centroid into lon/lat columns."""
    row = con.execute(
        "SELECT countries, activation_time, lon, lat, centroid_wkt "
        "FROM activations WHERE code = 'EMSR002'"
    ).fetchone()
    (countries, activation_time, lon, lat, centroid_wkt) = row

    # NOTE: `concat_ws` receives the country list as a single argument and
    # stringifies it, so the brackets are part of the stored value. See
    # `test_load_sql_should_join_countries_without_brackets`.
    assert countries == "[France, Spain]"
    assert activation_time == "2023-06-15"
    assert lon == pytest.approx(2.0)
    assert lat == pytest.approx(43.0)
    assert centroid_wkt == "POINT (2.0 43.0)"


@pytest.mark.xfail(
    strict=True,
    reason="LOAD_SQL uses concat_ws(', ', countries), which stringifies the list "
    "instead of joining it; array_to_string(countries, ', ') is the fix.",
)
def test_load_sql_should_join_countries_without_brackets(con):
    """Multi-country activations should render as a plain comma-separated string."""
    (countries,) = con.execute(
        "SELECT countries FROM activations WHERE code = 'EMSR002'"
    ).fetchone()

    assert countries == "France, Spain"


def test_load_sql_is_idempotent(con, tmp_path):
    """Re-running the load replaces the table rather than appending to it."""
    source = tmp_path / "again.json"
    source.write_text(json.dumps(ACTIVATIONS))

    con.execute(LOAD_SQL.format(path=source.as_posix()))
    (count,) = con.execute(COUNT_ACTIVATIONS).fetchone()

    assert count == len(ACTIVATIONS)


def test_list_wildfires_excludes_other_categories(con):
    """Only activations whose category mentions a wildfire are returned."""
    codes = {row[0] for row in list_wildfires(con, include_active=True)}

    assert codes == {"EMSR001", "EMSR002", "EMSR003"}


def test_list_wildfires_excludes_active_by_default(con):
    """Open activations are filtered out unless explicitly requested."""
    codes = [row[0] for row in list_wildfires(con)]

    assert codes == ["EMSR001", "EMSR002"]


def test_list_wildfires_orders_by_activation_time_descending(con):
    """The most recent activation comes first."""
    codes = [row[0] for row in list_wildfires(con, include_active=True)]

    assert codes == ["EMSR003", "EMSR001", "EMSR002"]


def test_list_wildfires_honours_the_limit(con):
    """`limit` caps the number of returned rows."""
    rows = list_wildfires(con, limit=2, include_active=True)

    assert len(rows) == 2


def test_list_wildfires_returns_the_table_columns(con):
    """Each row carries the columns the CLI table renderer expects."""
    (row,) = list_wildfires(con, limit=1)
    (code, name, countries, activation_time, closed, lon, lat) = row

    assert code == "EMSR001"
    assert name == "Closed wildfire, Italy"
    assert countries == "[Italy]"
    assert activation_time == "2024-07-01"
    assert closed is True
    assert (lon, lat) == (pytest.approx(9.5), pytest.approx(40.5))


def test_list_wildfires_rejects_a_non_numeric_limit(con):
    """`limit` is coerced to an int, so it cannot be used to inject SQL."""
    with pytest.raises(ValueError):
        list_wildfires(con, limit="1; DROP TABLE activations")


def test_create_folder_if_missing_is_idempotent(tmp_path):
    """Creating the parent folder twice is not an error."""
    target = tmp_path / "a" / "b" / "file.duckdb"

    _create_folder_if_missing(str(target))
    _create_folder_if_missing(str(target))

    assert target.parent.is_dir()
