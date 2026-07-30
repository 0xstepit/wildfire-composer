import json
import tempfile
from pathlib import Path

import httpx

from wildfire_composer.db import COUNT_ACTIVATIONS, LOAD_SQL, connect

TMP_FILENAME = "activations.json"


def fetch_all(url: str, page_size: int = 200, timeout: float = 60.0) -> list[dict]:
    """Fetch all the CEMS activations at the provided endpoint."""
    records: list[dict] = []
    offset = 0
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        while True:
            resp = client.get(url, params={"limit": page_size, "offset": offset})
            resp.raise_for_status()
            payload = resp.json()
            records.extend(payload.get("results", []))
            if not payload.get("next"):
                break
            offset += page_size
    return records


def refresh(url: str, db_path) -> int:
    """Create or refresh an activations table in the database."""
    records = fetch_all(url)

    con = connect(db_path)

    tmp = Path(tempfile.mkdtemp()) / TMP_FILENAME
    tmp.write_text(json.dumps(records))
    try:
        con.execute(LOAD_SQL.format(path=tmp.as_posix()))

        count = 0
        resp = con.execute(COUNT_ACTIVATIONS).fetchone()
        if resp is not None:
            (count,) = resp
    finally:
        con.close()
        tmp.unlink(missing_ok=True)

    return count
