"""Tests for `wildfire_composer.fetch`."""

import json

import duckdb
import httpx
import pytest

from wildfire_composer.db import connect, list_wildfires
from wildfire_composer.fetch import fetch_all, fetch_extended_activation, refresh

URL = "https://example.invalid/activations/"


def _record(code: str) -> dict:
    """A minimal activation record accepted by `LOAD_SQL`."""
    return {
        "code": code,
        "name": f"Wildfire {code}",
        "countries": ["Italy"],
        "category": "Wildfire",
        "activationTime": "2024-07-01T10:00:00",
        "centroid": "POINT (9.5 40.5)",
        "closed": True,
    }


def _paged_handler(pages, seen=None):
    """Serve `pages` (a list of result lists) and record the requests seen."""

    def handler(request):
        offset = int(request.url.params["offset"])
        limit = int(request.url.params["limit"])
        if seen is not None:
            seen.append((limit, offset))
        index = offset // limit
        results = pages[index] if index < len(pages) else []
        return httpx.Response(
            200,
            json={"results": results, "next": index + 1 < len(pages)},
        )

    return handler


def test_fetch_all_single_page(mock_http):
    """A response without a `next` marker terminates the loop."""
    mock_http(_paged_handler([[_record("EMSR001"), _record("EMSR002")]]))

    records = fetch_all(URL)

    assert [record["code"] for record in records] == ["EMSR001", "EMSR002"]


def test_fetch_all_follows_pagination(mock_http):
    """All the pages are concatenated, in order."""
    pages = [[_record("EMSR001")], [_record("EMSR002")], [_record("EMSR003")]]
    seen: list[tuple[int, int]] = []
    mock_http(_paged_handler(pages, seen))

    records = fetch_all(URL, page_size=1)

    assert [record["code"] for record in records] == [
        "EMSR001",
        "EMSR002",
        "EMSR003",
    ]
    assert seen == [(1, 0), (1, 1), (1, 2)]


def test_fetch_all_advances_the_offset_by_page_size(mock_http):
    """The offset moves by `page_size`, not by the number of returned records."""
    seen: list[tuple[int, int]] = []
    mock_http(_paged_handler([[_record("EMSR001")], []], seen))

    fetch_all(URL, page_size=200)

    assert seen == [(200, 0), (200, 200)]


def test_fetch_all_empty_payload(mock_http):
    """A payload with neither results nor a next page yields an empty list."""
    mock_http(lambda request: httpx.Response(200, json={}))

    assert fetch_all(URL) == []


def test_fetch_all_raises_on_http_error(mock_http):
    """A non-2xx response propagates as an `HTTPStatusError`."""
    mock_http(lambda request: httpx.Response(500, json={}))

    with pytest.raises(httpx.HTTPStatusError):
        fetch_all(URL)


def test_fetch_all_follows_redirects(mock_http):
    """A redirect to the real endpoint is followed transparently."""

    def handler(request):
        if request.url.path == "/old/":
            return httpx.Response(302, headers={"Location": URL})
        return httpx.Response(200, json={"results": [_record("EMSR001")]})

    mock_http(handler)

    records = fetch_all("https://example.invalid/old/")

    assert [record["code"] for record in records] == ["EMSR001"]


def test_fetch_extended_activation_returns_the_first_result(mock_http):
    """The endpoint is queried by code and the first record is returned."""
    seen: list[str] = []

    def handler(request):
        seen.append(request.url.params["code"])
        return httpx.Response(
            200, json={"results": [{"code": "EMSR999"}, {"code": "other"}]}
        )

    mock_http(handler)

    record = fetch_extended_activation(URL, "EMSR999")

    assert record == {"code": "EMSR999"}
    assert seen == ["EMSR999"]


def test_fetch_extended_activation_unknown_code(mock_http):
    """An unknown code currently surfaces as an `IndexError`."""
    mock_http(lambda request: httpx.Response(200, json={"results": []}))

    with pytest.raises(IndexError):
        fetch_extended_activation(URL, "EMSR000")


def test_fetch_extended_activation_raises_on_http_error(mock_http):
    """A non-2xx response propagates as an `HTTPStatusError`."""
    mock_http(lambda request: httpx.Response(404, json={}))

    with pytest.raises(httpx.HTTPStatusError):
        fetch_extended_activation(URL, "EMSR000")


@pytest.mark.network
def test_refresh_loads_the_activations_and_returns_the_count(mock_http, tmp_path):
    """`refresh` stores every fetched activation and reports how many landed."""
    records = [_record(f"EMSR00{i}") for i in range(1, 4)]
    mock_http(_paged_handler([records]))
    db_path = str(tmp_path / "db" / "cems.duckdb")

    count = refresh(URL, db_path)

    assert count == 3

    con = connect(db_path)
    try:
        assert len(list_wildfires(con)) == 3
    finally:
        con.close()


@pytest.mark.network
def test_refresh_replaces_previous_contents(mock_http, tmp_path):
    """Refreshing twice does not duplicate rows."""
    db_path = str(tmp_path / "cems.duckdb")
    mock_http(_paged_handler([[_record("EMSR001"), _record("EMSR002")]]))
    refresh(URL, db_path)

    mock_http(_paged_handler([[_record("EMSR003")]]))
    count = refresh(URL, db_path)

    assert count == 1


@pytest.mark.network
def test_refresh_releases_the_connection(mock_http, tmp_path):
    """The database is closed afterwards, so another process can open it."""
    mock_http(_paged_handler([[_record("EMSR001")]]))
    db_path = str(tmp_path / "cems.duckdb")

    refresh(URL, db_path)

    duckdb.connect(db_path, read_only=True).close()


@pytest.mark.network
def test_refresh_cleans_up_the_temporary_file(mock_http, tmp_path, monkeypatch):
    """The intermediate JSON dump is removed once the load completes."""
    mock_http(_paged_handler([[_record("EMSR001")]]))
    spool = tmp_path / "spool"
    spool.mkdir()
    monkeypatch.setattr("tempfile.mkdtemp", lambda *a, **kw: str(spool))

    refresh(URL, str(tmp_path / "cems.duckdb"))

    assert list(spool.iterdir()) == []


@pytest.mark.network
def test_refresh_cleans_up_after_a_failed_load(mock_http, tmp_path, monkeypatch):
    """A malformed payload still leaves no temporary file behind."""
    mock_http(lambda request: httpx.Response(200, json={"results": [{"nope": 1}]}))
    spool = tmp_path / "spool"
    spool.mkdir()
    monkeypatch.setattr("tempfile.mkdtemp", lambda *a, **kw: str(spool))

    with pytest.raises(Exception):
        refresh(URL, str(tmp_path / "cems.duckdb"))

    assert list(spool.iterdir()) == []


class FakeConnection:
    """A stand-in for a DuckDB connection that records the executed queries."""

    def __init__(self, count=0):
        self.queries: list[str] = []
        self.closed = False
        self._count = count
        self.payloads: list[list[dict]] = []

    def execute(self, query):
        """Record the query and, for the load, snapshot the JSON file it reads."""
        self.queries.append(query)
        if "read_json_auto" in query:
            path = query.split("read_json_auto('")[1].split("'")[0]
            self.payloads.append(json.loads(open(path).read()))
        return self

    def fetchone(self):
        """Return the row the `COUNT_ACTIVATIONS` query would produce."""
        return self._count

    def close(self):
        """Mark the connection as released."""
        self.closed = True


@pytest.fixture
def fake_connection(monkeypatch):
    """Replace `fetch.connect` with a `FakeConnection` factory."""
    from wildfire_composer import fetch as fetch_module

    def install(count=(0,)):
        con = FakeConnection(count)
        monkeypatch.setattr(fetch_module, "connect", lambda path: con)
        return con

    return install


def test_refresh_writes_valid_json_for_duckdb(mock_http, fake_connection, tmp_path):
    """The temporary file handed to DuckDB is a JSON array of the records."""
    mock_http(_paged_handler([[_record("EMSR001"), _record("EMSR002")]]))
    con = fake_connection((2,))

    count = refresh(URL, str(tmp_path / "cems.duckdb"))

    assert count == 2
    assert con.payloads == [[_record("EMSR001"), _record("EMSR002")]]
    assert con.closed is True


def test_refresh_returns_zero_when_the_count_is_unavailable(
    mock_http, fake_connection, tmp_path
):
    """A `None` result from the count query degrades to 0 rather than raising."""
    mock_http(_paged_handler([[_record("EMSR001")]]))
    fake_connection(None)

    assert refresh(URL, str(tmp_path / "cems.duckdb")) == 0


def test_refresh_closes_the_connection_when_the_load_fails(
    mock_http, fake_connection, tmp_path, monkeypatch
):
    """The connection is released even if the load query raises."""
    mock_http(_paged_handler([[_record("EMSR001")]]))
    con = fake_connection((1,))
    monkeypatch.setattr(
        con, "execute", lambda query: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    with pytest.raises(RuntimeError):
        refresh(URL, str(tmp_path / "cems.duckdb"))

    assert con.closed is True
