"""Load the synthetic dataset into SQLite.

SQLite is a whole database in a single file (or in memory). The MCP tools query it by
identifier, which is the "lookup" side of the experiment this repository runs.
"""

import json
import sqlite3
from pathlib import Path

from supplier_docs.models import Dataset

SCHEMA = """
CREATE TABLE suppliers (
    supplier_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    country     TEXT NOT NULL,
    city        TEXT NOT NULL,
    approved    INTEGER NOT NULL
);
CREATE TABLE products (
    code              TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    supplier_id       TEXT NOT NULL REFERENCES suppliers(supplier_id),
    category          TEXT NOT NULL,
    allergens         TEXT NOT NULL,  -- JSON list
    shelf_life_months INTEGER NOT NULL,
    specs             TEXT NOT NULL   -- JSON list of {parameter, unit, min, max}
);
CREATE TABLE certificates (
    certificate_id TEXT PRIMARY KEY,
    supplier_id    TEXT NOT NULL REFERENCES suppliers(supplier_id),
    scheme         TEXT NOT NULL,
    number         TEXT NOT NULL,
    issued         TEXT NOT NULL,     -- ISO date
    expires        TEXT NOT NULL      -- ISO date
);
CREATE TABLE lots (
    lot_id          TEXT PRIMARY KEY,
    product_code    TEXT NOT NULL REFERENCES products(code),
    production_date TEXT NOT NULL,    -- ISO date
    results         TEXT NOT NULL     -- JSON object {parameter: value}
);
"""


def build_database(dataset: Dataset, path: Path | str = ":memory:") -> sqlite3.Connection:
    """Create a fresh database from `dataset` and return an open connection to it."""
    if isinstance(path, Path) and path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    with conn:
        conn.executemany(
            "INSERT INTO suppliers VALUES (?, ?, ?, ?, ?)",
            [
                (s.supplier_id, s.name, s.country, s.city, int(s.approved))
                for s in dataset.suppliers
            ],
        )
        conn.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    p.code,
                    p.name,
                    p.supplier_id,
                    p.category,
                    json.dumps(list(p.allergens)),
                    p.shelf_life_months,
                    json.dumps([s.model_dump() for s in p.specs]),
                )
                for p in dataset.products
            ],
        )
        conn.executemany(
            "INSERT INTO certificates VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    c.certificate_id,
                    c.supplier_id,
                    c.scheme.value,
                    c.number,
                    c.issued.isoformat(),
                    c.expires.isoformat(),
                )
                for c in dataset.certificates
            ],
        )
        conn.executemany(
            "INSERT INTO lots VALUES (?, ?, ?, ?)",
            [
                (
                    lot.lot_id,
                    lot.product_code,
                    lot.production_date.isoformat(),
                    json.dumps(lot.results),
                )
                for lot in dataset.lots
            ],
        )
    return conn
