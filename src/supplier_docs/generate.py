"""Generate the synthetic dataset for Huerta Norte S.L., a fictional food canner.

Every company, product, certificate and lot is invented. The generator uses a fixed
seed, so running it twice produces byte-identical files. CI checks that the committed
files in `data/` match a fresh run.

Usage:
    uv run generate-data            # writes data/dataset.json and data/documents/
    uv run generate-data --out tmp  # writes somewhere else
"""

import argparse
import json
import random
import shutil
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from supplier_docs.models import (
    Certificate,
    Dataset,
    Lot,
    Product,
    Scheme,
    SpecLimit,
    Supplier,
)

SEED = 20261008
REFERENCE_DATE = date(2026, 10, 1)
N_SUPPLIERS = 20
PRODUCTS_PER_SUPPLIER = 3
LOTS_PER_PRODUCT = 2


@dataclass(frozen=True)
class Category:
    name: str
    trade_name: str  # first word of a supplier's company name
    products: tuple[str, ...]
    allergens: tuple[str, ...]
    shelf_life_months: int
    specs: tuple[SpecLimit, ...]


CATEGORIES: tuple[Category, ...] = (
    Category(
        name="tomato",
        trade_name="Conservas",
        products=("Crushed tomato", "Tomato paste", "Peeled whole tomato"),
        allergens=(),
        shelf_life_months=36,
        specs=(
            SpecLimit(parameter="pH", unit="pH", min=4.0, max=4.5),
            SpecLimit(parameter="Brix", unit="°Bx", min=5.0, max=30.0),
        ),
    ),
    Category(
        name="legumes",
        trade_name="Legumbres",
        products=("Cooked chickpeas", "Cooked white beans", "Cooked lentils"),
        allergens=(),
        shelf_life_months=48,
        specs=(
            SpecLimit(parameter="pH", unit="pH", min=5.5, max=6.8),
            SpecLimit(parameter="Salt", unit="%", max=1.2),
        ),
    ),
    Category(
        name="fish",
        trade_name="Pescados",
        products=("Tuna in olive oil", "Sardines in tomato sauce", "Mackerel fillets"),
        allergens=("fish",),
        shelf_life_months=48,
        specs=(
            SpecLimit(parameter="Histamine", unit="mg/kg", max=100.0),
            SpecLimit(parameter="Salt", unit="%", max=2.0),
        ),
    ),
    Category(
        name="vegetables",
        trade_name="Hortícola",
        products=("Roasted red peppers", "Artichoke hearts", "White asparagus"),
        allergens=("sulphites",),
        shelf_life_months=36,
        specs=(
            SpecLimit(parameter="pH", unit="pH", max=4.6),
            SpecLimit(parameter="Sulphites", unit="mg/kg", max=50.0),
        ),
    ),
    Category(
        name="fruit",
        trade_name="Frutas",
        products=("Peaches in syrup", "Pears in light syrup", "Apricot halves"),
        allergens=(),
        shelf_life_months=24,
        specs=(
            SpecLimit(parameter="Brix", unit="°Bx", min=14.0, max=20.0),
            SpecLimit(parameter="pH", unit="pH", min=3.4, max=4.2),
        ),
    ),
)

NAME_SUFFIXES = (
    "del Cierzo",
    "Ribera Alta",
    "Vega Clara",
    "Monte Ardal",
    "Los Almendros",
    "Peña Roja",
    "Valdecanto",
    "Río Lucio",
    "Altozano",
    "Mar de Ostia",
    "Campo Sereno",
    "Las Torcas",
    "Fuente Mora",
    "Val de Ruedo",
    "Cabo Lince",
    "Santa Olaria",
    "Prado Hondo",
    "Los Tejares",
    "Sierra Brava",
    "Llano Verde",
)
LEGAL_FORMS = {"Spain": "S.L.", "Portugal": "Lda.", "Italy": "S.r.l.", "Morocco": "S.A.R.L."}
LOCATIONS = (
    ("Spain", "Calahorra"),
    ("Spain", "Tudela"),
    ("Spain", "Murcia"),
    ("Spain", "Vigo"),
    ("Spain", "Mérida"),
    ("Spain", "Almería"),
    ("Portugal", "Leiria"),
    ("Italy", "Salerno"),
    ("Morocco", "Agadir"),
)


def make_suppliers(rng: random.Random, categories: list[Category]) -> list[Supplier]:
    if len(categories) > len(NAME_SUFFIXES):
        raise ValueError(f"Add names: {len(categories)} suppliers, {len(NAME_SUFFIXES)} suffixes")
    suffixes = rng.sample(NAME_SUFFIXES, k=len(NAME_SUFFIXES))
    suppliers: list[Supplier] = []
    for i, category in enumerate(categories):
        country, city = rng.choice(LOCATIONS)
        legal_form = LEGAL_FORMS[country]
        # Every supplier gets its own suffix, so names are unique.
        suffix = suffixes[i]
        suppliers.append(
            Supplier(
                supplier_id=f"SUP-{i + 1:03d}",
                name=f"{category.trade_name} {suffix} {legal_form}",
                country=country,
                city=city,
                # One supplier in ten is still pending approval.
                approved=(i + 1) % 10 != 0,
            )
        )
    return suppliers


def make_products(suppliers: list[Supplier], categories: list[Category]) -> list[Product]:
    products: list[Product] = []
    code = 1001
    for supplier, category in zip(suppliers, categories, strict=True):
        for name in category.products[:PRODUCTS_PER_SUPPLIER]:
            products.append(
                Product(
                    code=f"P-{code}",
                    name=name,
                    supplier_id=supplier.supplier_id,
                    category=category.name,
                    allergens=category.allergens,
                    shelf_life_months=category.shelf_life_months,
                    specs=category.specs,
                )
            )
            code += 1
    return products


def make_certificates(rng: random.Random, suppliers: list[Supplier]) -> list[Certificate]:
    """One or two certificates per supplier, all valid on REFERENCE_DATE.

    Issue #1 extends this function so that some certificates are already expired.
    """
    certificates: list[Certificate] = []
    for supplier in suppliers:
        schemes = rng.sample(list(Scheme), k=rng.choice((1, 2)))
        for scheme in schemes:
            issued = REFERENCE_DATE - timedelta(days=rng.randint(30, 700))
            expires = issued + timedelta(days=3 * 365)
            certificates.append(
                Certificate(
                    certificate_id=f"CERT-{len(certificates) + 1:04d}",
                    supplier_id=supplier.supplier_id,
                    scheme=scheme,
                    number=f"{scheme.name}-{rng.randint(100000, 999999)}",
                    issued=issued,
                    expires=expires,
                )
            )
    return certificates


def in_range_value(rng: random.Random, limit: SpecLimit) -> float:
    """A value comfortably inside the limit, rounded to 2 decimals."""
    # SpecLimit guarantees at least one bound; an open side gets a plausible stand-in.
    low = limit.min if limit.min is not None else (limit.max or 0.0) * 0.5
    high = limit.max if limit.max is not None else low * 2
    margin = (high - low) * 0.1
    return round(rng.uniform(low + margin, high - margin), 2)


def make_lots(rng: random.Random, products: list[Product]) -> list[Lot]:
    """LOTS_PER_PRODUCT lots per product, every result inside its spec.

    Issue #1 extends this function so that some lots fail their spec.
    """
    lots: list[Lot] = []
    for product in products:
        for _ in range(LOTS_PER_PRODUCT):
            produced = REFERENCE_DATE - timedelta(days=rng.randint(10, 400))
            lots.append(
                Lot(
                    lot_id=f"L{produced:%y%m}-{len(lots) + 1:04d}",
                    product_code=product.code,
                    production_date=produced,
                    results={s.parameter: in_range_value(rng, s) for s in product.specs},
                )
            )
    return lots


def build_dataset(seed: int = SEED) -> Dataset:
    rng = random.Random(seed)
    categories = [rng.choice(CATEGORIES) for _ in range(N_SUPPLIERS)]
    suppliers = make_suppliers(rng, categories)
    products = make_products(suppliers, categories)
    certificates = make_certificates(rng, suppliers)
    lots = make_lots(rng, products)
    return Dataset(
        reference_date=REFERENCE_DATE,
        suppliers=tuple(suppliers),
        products=tuple(products),
        certificates=tuple(certificates),
        lots=tuple(lots),
    )


def render_product_sheet(product: Product, supplier: Supplier) -> str:
    allergens = ", ".join(product.allergens) if product.allergens else "none declared"
    rows = "\n".join(
        f"| {s.parameter} | {s.unit} | {'' if s.min is None else s.min} "
        f"| {'' if s.max is None else s.max} |"
        for s in product.specs
    )
    return (
        f"# Technical data sheet: {product.name}\n\n"
        f"- Product code: {product.code}\n"
        f"- Supplier: {supplier.name} ({supplier.supplier_id})\n"
        f"- Category: {product.category}\n"
        f"- Allergens: {allergens}\n"
        f"- Shelf life: {product.shelf_life_months} months\n\n"
        f"## Specifications\n\n"
        f"| Parameter | Unit | Min | Max |\n|---|---|---|---|\n{rows}\n"
    )


def render_certificate(cert: Certificate, supplier: Supplier) -> str:
    return (
        f"# Certificate {cert.certificate_id}\n\n"
        f"- Scheme: {cert.scheme.value}\n"
        f"- Certificate number: {cert.number}\n"
        f"- Holder: {supplier.name} ({supplier.supplier_id}), {supplier.city}, "
        f"{supplier.country}\n"
        f"- Issued: {cert.issued.isoformat()}\n"
        f"- Expires: {cert.expires.isoformat()}\n"
    )


def write_dataset(dataset: Dataset, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dataset.json").write_text(
        json.dumps(dataset.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    docs_dir = out_dir / "documents"
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir()
    by_id = {s.supplier_id: s for s in dataset.suppliers}
    for product in dataset.products:
        text = render_product_sheet(product, by_id[product.supplier_id])
        (docs_dir / f"sheet-{product.code}.md").write_text(text, encoding="utf-8")
    for cert in dataset.certificates:
        text = render_certificate(cert, by_id[cert.supplier_id])
        (docs_dir / f"certificate-{cert.certificate_id}.md").write_text(text, encoding="utf-8")


def load_dataset(path: Path) -> Dataset:
    return Dataset.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("data"))
    args = parser.parse_args()
    dataset = build_dataset()
    write_dataset(dataset, args.out)
    print(
        f"Wrote {len(dataset.suppliers)} suppliers, {len(dataset.products)} products, "
        f"{len(dataset.certificates)} certificates and {len(dataset.lots)} lots to {args.out}"
    )


if __name__ == "__main__":
    main()
