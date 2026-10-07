import json
from pathlib import Path

from supplier_docs.generate import (
    LOTS_PER_PRODUCT,
    N_SUPPLIERS,
    PRODUCTS_PER_SUPPLIER,
    build_dataset,
    load_dataset,
    write_dataset,
)
from supplier_docs.models import Dataset

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_sizes(dataset: Dataset) -> None:
    assert len(dataset.suppliers) == N_SUPPLIERS
    assert len(dataset.products) == N_SUPPLIERS * PRODUCTS_PER_SUPPLIER
    assert len(dataset.lots) == len(dataset.products) * LOTS_PER_PRODUCT
    assert len(dataset.certificates) >= N_SUPPLIERS


def test_identifiers_are_unique(dataset: Dataset) -> None:
    for ids in (
        [s.supplier_id for s in dataset.suppliers],
        [s.name for s in dataset.suppliers],
        [p.code for p in dataset.products],
        [c.certificate_id for c in dataset.certificates],
        [lot.lot_id for lot in dataset.lots],
    ):
        assert len(ids) == len(set(ids))


def test_every_lot_reports_every_spec_parameter(dataset: Dataset) -> None:
    products = {p.code: p for p in dataset.products}
    for lot in dataset.lots:
        expected = {s.parameter for s in products[lot.product_code].specs}
        assert set(lot.results) == expected


def test_generation_is_deterministic() -> None:
    assert build_dataset() == build_dataset()


def test_a_different_seed_gives_different_data() -> None:
    assert build_dataset(seed=1) != build_dataset(seed=2)


def test_round_trip_through_files(tmp_path: Path, dataset: Dataset) -> None:
    write_dataset(dataset, tmp_path)
    assert load_dataset(tmp_path / "dataset.json") == dataset
    documents = list((tmp_path / "documents").glob("*.md"))
    assert len(documents) == len(dataset.products) + len(dataset.certificates)


def test_committed_data_is_up_to_date(tmp_path: Path, dataset: Dataset) -> None:
    """If this fails, run `uv run generate-data` and commit the result."""
    write_dataset(dataset, tmp_path)
    committed = json.loads((DATA_DIR / "dataset.json").read_text(encoding="utf-8"))
    fresh = json.loads((tmp_path / "dataset.json").read_text(encoding="utf-8"))
    assert committed == fresh
    committed_docs = sorted(p.name for p in (DATA_DIR / "documents").glob("*.md"))
    fresh_docs = sorted(p.name for p in (tmp_path / "documents").glob("*.md"))
    assert committed_docs == fresh_docs
    for name in fresh_docs:
        assert (DATA_DIR / "documents" / name).read_text(encoding="utf-8") == (
            tmp_path / "documents" / name
        ).read_text(encoding="utf-8")
