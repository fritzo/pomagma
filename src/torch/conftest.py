import os

import pytest
import torch

from pomagma.torch.language import Language
from pomagma.torch.structure import Structure

# Path to test data file
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEST_FILE = os.path.join(ROOT, "bootstrap", "atlas", "skrj", "region.normal.2047.pb")


@pytest.fixture(scope="session")
def structure() -> Structure:
    """Load a real structure from bootstrap data for testing."""
    return Structure.load(TEST_FILE, relations=False)


@pytest.fixture(scope="session")
def language(structure: Structure) -> Language:
    """Create a test language with realistic weights."""
    # Use 1 + item_count because objects are 1-indexed (0 means undefined)
    nullary_functions = torch.zeros(1 + structure.item_count, dtype=torch.float32)
    nullary_functions[structure.nullary_functions["S"]] = 0.1
    nullary_functions[structure.nullary_functions["K"]] = 0.1
    nullary_functions[structure.nullary_functions["J"]] = 0.1
    nullary_functions[structure.nullary_functions["R"]] = 0.1
    binary_functions = {
        "APP": torch.tensor(0.2, dtype=torch.float32),
        "COMP": torch.tensor(0.2, dtype=torch.float32),
    }
    symmetric_functions = {
        "JOIN": torch.tensor(0.2, dtype=torch.float32),
    }
    language = Language(
        nullary_functions=nullary_functions,
        binary_functions=binary_functions,
        symmetric_functions=symmetric_functions,
    )
    return language
