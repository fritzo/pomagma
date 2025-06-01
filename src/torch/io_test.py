import logging
import os

import pytest
import torch

from pomagma.atlas.structure_pb2 import ObMap, ObSet

from .io import delta_decompress, load_dense_set
from .structure import Structure

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEST_FILE = os.path.join(ROOT, "bootstrap", "atlas", "skrj", "region.normal.2047.pb")


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


@pytest.mark.parametrize("filename", [TEST_FILE])
def test_structure_loading(filename: str) -> None:
    logger.info(f"Loading structure from {filename}...")
    structure = Structure.load(filename, relations=True)

    logger.info("Structure loaded successfully!")
    logger.info(f"  Name: {structure.name}")
    logger.info(f"  Item count: {structure.item_count}")
    logger.info(f"  Nullary functions: {len(structure.nullary_functions)}")
    logger.info(f"  Binary functions: {len(structure.binary_functions)}")
    logger.info(f"  Symmetric functions: {len(structure.symmetric_functions)}")
    logger.info(f"  Unary relations: {len(structure.unary_relations)}")
    logger.info(f"  Binary relations: {len(structure.binary_relations)}")

    # Print some details about the loaded data
    for name, val in structure.nullary_functions.items():
        logger.info(f"    Nullary function '{name}': {val}")

    for name, func in structure.binary_functions.items():
        Vlr_entries = func.Vlr.ptrs[-1].item()
        logger.info(f"    Binary function '{name}': Vlr has {Vlr_entries} entries")

    for name, func in structure.symmetric_functions.items():
        Vlr_entries = func.Vlr.ptrs[-1].item()
        logger.info(f"    Symmetric function '{name}': Vlr has {Vlr_entries} entries")

    for name, tensor in structure.unary_relations.items():
        non_zero = torch.count_nonzero(tensor)
        logger.info(
            f"    Unary relation '{name}': "
            f"shape {tensor.shape}, {non_zero} non-zero entries"
        )

    for name, tensor in structure.binary_relations.items():
        non_zero = torch.count_nonzero(tensor)
        logger.info(
            f"    Binary relation '{name}': "
            f"shape {tensor.shape}, {non_zero} non-zero entries"
        )
