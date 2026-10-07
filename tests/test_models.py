from datetime import date

import pytest
from pydantic import ValidationError

from supplier_docs.models import Certificate, Scheme, SpecLimit


def test_spec_limit_needs_a_bound() -> None:
    with pytest.raises(ValidationError):
        SpecLimit(parameter="pH", unit="pH")


def test_spec_limit_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError):
        SpecLimit(parameter="pH", unit="pH", min=5.0, max=4.0)


@pytest.mark.parametrize(
    ("value", "accepted"),
    [(3.9, False), (4.0, True), (4.3, True), (4.5, True), (4.51, False)],
)
def test_spec_limit_bounds_are_inclusive(value: float, accepted: bool) -> None:
    limit = SpecLimit(parameter="pH", unit="pH", min=4.0, max=4.5)
    assert limit.accepts(value) is accepted


def test_open_ended_limit() -> None:
    limit = SpecLimit(parameter="Histamine", unit="mg/kg", max=100.0)
    assert limit.accepts(0.0)
    assert not limit.accepts(100.1)


def test_certificate_validity_window() -> None:
    cert = Certificate(
        certificate_id="CERT-0001",
        supplier_id="SUP-001",
        scheme=Scheme.IFS,
        number="IFS-123456",
        issued=date(2025, 1, 1),
        expires=date(2026, 1, 1),
    )
    assert cert.is_valid_on(date(2026, 1, 1))
    assert not cert.is_valid_on(date(2026, 1, 2))
    assert not cert.is_valid_on(date(2024, 12, 31))
