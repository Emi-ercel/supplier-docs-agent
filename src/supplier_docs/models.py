"""Domain models for the synthetic quality-department dataset.

Everything here is plain data: no I/O, no database, no model calls.
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Scheme(StrEnum):
    """Food-safety certification schemes a supplier can hold."""

    IFS = "IFS Food"
    BRCGS = "BRCGS Food Safety"
    FSSC = "FSSC 22000"
    ISO_22000 = "ISO 22000"


class Supplier(Frozen):
    supplier_id: str = Field(pattern=r"^SUP-\d{3}$")
    name: str
    country: str
    city: str
    approved: bool


class SpecLimit(Frozen):
    """Acceptance range for one analytical parameter. A missing bound means 'no limit'."""

    parameter: str
    unit: str
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def _has_a_bound(self) -> "SpecLimit":
        if self.min is None and self.max is None:
            raise ValueError(f"{self.parameter}: a limit needs at least a min or a max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"{self.parameter}: min {self.min} is greater than max {self.max}")
        return self

    def accepts(self, value: float) -> bool:
        if self.min is not None and value < self.min:
            return False
        return not (self.max is not None and value > self.max)


class Product(Frozen):
    code: str = Field(pattern=r"^P-\d{4}$")
    name: str
    supplier_id: str
    category: str
    allergens: tuple[str, ...]
    shelf_life_months: int = Field(gt=0)
    specs: tuple[SpecLimit, ...]

    def spec(self, parameter: str) -> SpecLimit:
        for limit in self.specs:
            if limit.parameter == parameter:
                return limit
        raise KeyError(f"{self.code} has no spec for {parameter!r}")


class Certificate(Frozen):
    certificate_id: str = Field(pattern=r"^CERT-\d{4}$")
    supplier_id: str
    scheme: Scheme
    number: str
    issued: date
    expires: date

    def is_valid_on(self, day: date) -> bool:
        return self.issued <= day <= self.expires


class Lot(Frozen):
    lot_id: str = Field(pattern=r"^L\d{4}-\d{4}$")
    product_code: str
    production_date: date
    results: dict[str, float]


class Dataset(Frozen):
    """The whole synthetic world. `reference_date` is 'today' for every question."""

    reference_date: date
    suppliers: tuple[Supplier, ...]
    products: tuple[Product, ...]
    certificates: tuple[Certificate, ...]
    lots: tuple[Lot, ...]

    @model_validator(mode="after")
    def _references_exist(self) -> "Dataset":
        supplier_ids = {s.supplier_id for s in self.suppliers}
        product_codes = {p.code for p in self.products}
        for product in self.products:
            if product.supplier_id not in supplier_ids:
                raise ValueError(f"{product.code} points to unknown {product.supplier_id}")
        for cert in self.certificates:
            if cert.supplier_id not in supplier_ids:
                raise ValueError(f"{cert.certificate_id} points to unknown {cert.supplier_id}")
        for lot in self.lots:
            if lot.product_code not in product_codes:
                raise ValueError(f"{lot.lot_id} points to unknown {lot.product_code}")
        return self
