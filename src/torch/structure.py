from dataclasses import dataclass
from typing import Mapping, NewType

import torch

Ob = NewType("Ob", int)
"""An item in the carrier. 1-indexed, so 0 means undefined."""


@dataclass(frozen=True, slots=True, eq=False)
class Structure:
    """
    PyTorch representation of an algebraic structure. Immutable.

    Functions are in COO format:
    - Injective functions: shape [2, num_entries] with [inputs, outputs]
    - Binary/symmetric functions: shape [3, num_entries] with [arg1, arg2, outputs]

    Relations are dense:
    - Unary relations: shape [1 + item_count]
    - Binary relations: shape [1 + item_count, 1 + item_count]
    """

    name: str
    item_count: int
    nullary_functions: Mapping[str, Ob]
    injective_functions: Mapping[str, torch.Tensor]
    binary_functions: Mapping[str, torch.Tensor]
    symmetric_functions: Mapping[str, torch.Tensor]
    unary_relations: Mapping[str, torch.Tensor]
    binary_relations: Mapping[str, torch.Tensor]

    @staticmethod
    def load(filename: str, *, relations: bool = False) -> "Structure":
        """
        Load a structure from a protobuf file.
        """
        from .io import load_structure

        return load_structure(filename, relations=relations)
