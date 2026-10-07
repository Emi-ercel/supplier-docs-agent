"""Tests for issue #1. Remove the `skip` marker when you start the issue.

The agent needs "bad news" in the data so we can ask questions like
"Is supplier X's IFS certificate still valid?" or "Did lot Y pass its spec?"
and know the right answer is "no".
"""

import pytest

from supplier_docs.generate import build_dataset
from supplier_docs.models import Dataset

pytestmark = pytest.mark.skip(reason="Issue #1: not started yet")


def test_some_certificates_are_expired(dataset: Dataset) -> None:
    expired = [c for c in dataset.certificates if not c.is_valid_on(dataset.reference_date)]
    assert len(expired) >= 3


def test_most_suppliers_still_have_a_valid_certificate(dataset: Dataset) -> None:
    with_valid = {
        c.supplier_id for c in dataset.certificates if c.is_valid_on(dataset.reference_date)
    }
    assert len(with_valid) >= len(dataset.suppliers) - 3


def test_some_lots_fail_exactly_one_parameter(dataset: Dataset) -> None:
    products = {p.code: p for p in dataset.products}
    failing = []
    for lot in dataset.lots:
        product = products[lot.product_code]
        failed = [p for p, v in lot.results.items() if not product.spec(p).accepts(v)]
        assert len(failed) <= 1, f"{lot.lot_id} fails more than one parameter: {failed}"
        if failed:
            failing.append(lot.lot_id)
    assert len(failing) >= 2


def test_still_deterministic() -> None:
    assert build_dataset() == build_dataset()
