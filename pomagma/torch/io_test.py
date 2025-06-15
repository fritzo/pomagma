import logging

import pytest
import torch

from pomagma.atlas.structure_pb2 import ObMap, ObSet

from .io import delta_decompress, load_dense_set
from .structure import BOOTSTRAP, Structure

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def structure_cpp() -> Structure:
    return Structure.load(BOOTSTRAP, backend="cpp")


@pytest.fixture(scope="session")
def structure_py() -> Structure:
    return Structure.load(BOOTSTRAP, backend="python")


def test_delta_decompress() -> None:
    ob_map = ObMap()
    ob_map.key_diff_minus_one.extend([0, 1, 2])
    ob_map.val_diff.extend([10, 5, -3])

    keys, vals = delta_decompress(ob_map)

    expected_keys = [1, 3, 6]
    expected_vals = [10, 15, 12]

    assert keys == expected_keys, f"Expected keys {expected_keys}, got {keys}"
    assert vals == expected_vals, f"Expected vals {expected_vals}, got {vals}"


def test_dense_set_loading() -> None:
    ob_set = ObSet()
    ob_set.dense = bytes([0x2A])

    tensor = load_dense_set(ob_set, 7)

    # Check that the right bits are set
    expected = torch.zeros(8, dtype=torch.bool)
    expected[1] = True
    expected[3] = True
    expected[5] = True

    assert torch.equal(tensor, expected), f"Expected {expected}, got {tensor}"


def test_structure_loading(structure_cpp: Structure, structure_py: Structure) -> None:
    structure_cpp.assert_eq(structure_py)
