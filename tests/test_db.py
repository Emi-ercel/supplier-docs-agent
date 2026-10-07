import json

from supplier_docs.db import build_database
from supplier_docs.models import Dataset


def test_row_counts_match_dataset(dataset: Dataset) -> None:
    conn = build_database(dataset)
    for table, expected in (
        ("suppliers", len(dataset.suppliers)),
        ("products", len(dataset.products)),
        ("certificates", len(dataset.certificates)),
        ("lots", len(dataset.lots)),
    ):
        (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        assert count == expected, table


def test_product_row_round_trips(dataset: Dataset) -> None:
    conn = build_database(dataset)
    product = dataset.products[0]
    row = conn.execute("SELECT * FROM products WHERE code = ?", (product.code,)).fetchone()
    assert row["supplier_id"] == product.supplier_id
    assert json.loads(row["allergens"]) == list(product.allergens)
    assert [s["parameter"] for s in json.loads(row["specs"])] == [
        s.parameter for s in product.specs
    ]
