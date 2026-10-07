import pytest

from supplier_docs.generate import build_dataset
from supplier_docs.models import Dataset


@pytest.fixture(scope="session")
def dataset() -> Dataset:
    return build_dataset()
