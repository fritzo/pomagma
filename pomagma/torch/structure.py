import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NewType

import torch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BOOTSTRAP = os.path.join(ROOT, "bootstrap", "atlas", "skrj", "region.normal.2047.pb")
"""Path to the bootstrap structure file, for testing."""


Ob = NewType("Ob", int)
"""An item in the carrier. 1-indexed, so 0 means undefined."""


def assert_tensors_equal(a: torch.Tensor, b: torch.Tensor) -> None:
    assert a.shape == b.shape, f"Shapes do not match: {a.shape} != {b.shape}"
    assert a.dtype == b.dtype, f"Dtypes do not match: {a.dtype} != {b.dtype}"
    assert a.device == b.device, f"Devices do not match: {a.device} != {b.device}"
    assert torch.allclose(a, b)


class BinaryFunctionSumProduct(torch.autograd.Function):
    @staticmethod
    def forward(
        ctx,
        Vlr_ptrs: torch.Tensor,
        Vlr_args: torch.Tensor,
        Rvl_ptrs: torch.Tensor,
        Rvl_args: torch.Tensor,
        Lvr_ptrs: torch.Tensor,
        Lvr_args: torch.Tensor,
        lhs: torch.Tensor,
        rhs: torch.Tensor,
    ) -> torch.Tensor:
        val = torch.ops.pomagma.binary_function_sum_product(
            Vlr_ptrs, Vlr_args, lhs, rhs
        )
        ctx.save_for_backward(Rvl_ptrs, Rvl_args, Lvr_ptrs, Lvr_args, lhs, rhs)
        return val

    @staticmethod
    def backward(ctx, grad_val: torch.Tensor) -> tuple[torch.Tensor, ...]:
        Rvl_ptrs, Rvl_args, Lvr_ptrs, Lvr_args, lhs, rhs = ctx.saved_tensors
        grad_lhs = torch.ops.pomagma.binary_function_sum_product(
            Lvr_ptrs, Lvr_args, grad_val, rhs
        )
        grad_rhs = torch.ops.pomagma.binary_function_sum_product(
            Rvl_ptrs, Rvl_args, grad_val, lhs
        )
        return (None, None, None, None, None, None, grad_lhs, grad_rhs)


@dataclass(frozen=True, slots=True, eq=False)
class SparseBinaryFunction:
    """
    Sparse representation of a partial binary function.

    This is a linear-probe hash table.
    Zero denotes the undefined value.

    Fields:
        hash_table: Tensor of shape [H, 3] where H > N is the size of the hash table.
            hash_table[i, 0] is the left argument.
            hash_table[i, 1] is the right argument.
            hash_table[i, 2] is the value of the function.
    """

    hash_table: torch.Tensor

    def __init__(
        self, num_entries: int = 0, *, hash_table: torch.Tensor | None = None
    ) -> None:
        assert (num_entries > 0) == (hash_table is None)
        if hash_table is None:
            optimal_size = 2 ** (num_entries.bit_length() + 1)
            hash_table = torch.zeros(optimal_size, 3, dtype=torch.int32)
        object.__setattr__(self, "hash_table", hash_table)

    def assert_eq(self, other: "SparseBinaryFunction") -> None:
        assert_tensors_equal(self.hash_table, other.hash_table)

    def __getitem__(self, key: tuple[Ob, Ob]) -> Ob:
        lhs, rhs = key
        H = self.hash_table.size(0)
        h = abs(torch.ops.pomagma.hash_pair(lhs, rhs)) % H
        while self.hash_table[h, 0] != lhs or self.hash_table[h, 1] != rhs:
            if self.hash_table[h, 0] == 0:
                return Ob(0)
            h = (h + 1) % H
        return int(self.hash_table[h, 2])

    def __setitem__(self, key: tuple[Ob, Ob], val: Ob) -> None:
        lhs, rhs = key
        H = self.hash_table.size(0)
        h = abs(torch.ops.pomagma.hash_pair(lhs, rhs)) % H
        while self.hash_table[h, 0] != 0:
            h = (h + 1) % H
        self.hash_table[h, 0] = lhs
        self.hash_table[h, 1] = rhs
        self.hash_table[h, 2] = val


@dataclass(frozen=True, slots=True, eq=False)
class SparseTernaryRelation:
    """
    Sparse representation of a binary function table in compressed sparse row
    (CSR) format.

    This stores mappings from (X, Y) -> Z where the function is indexed by Z.
    For example, if we have f(X, Y) = Z, this stores all (X, Y) pairs that
    produce each Z.

    Fields:
        ptrs: Tensor of shape [N+1] where N is the size of the domain.
              ptrs[i] to ptrs[i+1] gives the range in args for output value i.
              This is the row pointer array in CSR format.
        args: Tensor of shape [nnz, 2] where nnz is the number of non-zero entries.
              Each row contains [X, Y] coordinates for the corresponding output.
              This is the column indices array in CSR format.
    """

    ptrs: torch.Tensor
    args: torch.Tensor

    def assert_eq(self, other: "SparseTernaryRelation") -> None:
        assert_tensors_equal(self.ptrs, other.ptrs)
        assert_tensors_equal(self.args, other.args)


@dataclass(frozen=True, slots=True, eq=False)
class BinaryFunction:
    """
    A binary function in the structure with support for automatic differentiation.

    Stores the function f(L, R) = V in four different sparse representations:
    - LRv: Maps (Left, Right) -> Value for deterministic lookup
    - Vlr: Maps Value -> (Left, Right) pairs for forward evaluation
    - Rvl: Maps Right -> (Value, Left) pairs for backward wrt right
    - Lvr: Maps Left -> (Value, Right) pairs for backward wrt left

    These three tables enable efficient forward and backward passes in autograd.
    """

    name: str
    LRv: SparseBinaryFunction  # (Left, Right) -> Value mapping for lookup
    Vlr: SparseTernaryRelation  # Value -> (Left, Right) pairs for forward pass
    Rvl: SparseTernaryRelation  # Right -> (Value, Left) pairs for backward wrt right
    Lvr: SparseTernaryRelation  # Left -> (Value, Right) pairs for backward wrt left

    def assert_eq(self, other: "BinaryFunction") -> None:
        assert self.name == other.name
        self.LRv.assert_eq(other.LRv)
        self.Vlr.assert_eq(other.Vlr)
        self.Rvl.assert_eq(other.Rvl)
        self.Lvr.assert_eq(other.Lvr)

    def __getitem__(self, key: tuple[Ob, Ob]) -> Ob:
        """Lookup the value of the function at the given (lhs, rhs) pair."""
        return self.LRv[key]

    def sum_product(self, lhs: torch.Tensor, rhs: torch.Tensor) -> torch.Tensor:
        """Differentiably convolve two weight vectors."""
        return BinaryFunctionSumProduct.apply(
            self.Vlr.ptrs,
            self.Vlr.args,
            self.Rvl.ptrs,
            self.Rvl.args,
            self.Lvr.ptrs,
            self.Lvr.args,
            lhs,
            rhs,
        )

    def distribute_product(
        self, parent_counts: torch.Tensor, probs: torch.Tensor, weight: float
    ) -> torch.Tensor:
        """
        Distribute parent occurrence counts to children based on probability weights.
        """
        return torch.ops.pomagma.binary_function_distribute_product(
            self.Vlr.ptrs,
            self.Vlr.args,
            parent_counts,
            probs,
            weight,
        )

    @torch.no_grad()
    def max_product(self, lhs: torch.Tensor, rhs: torch.Tensor) -> torch.Tensor:
        """Non-differentiably max-convolve two weight vectors."""
        return torch.ops.pomagma.binary_function_max_product(
            self.Vlr.ptrs, self.Vlr.args, lhs, rhs
        )


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False)
class Structure:
    """
    PyTorch representation of an algebraic structure. Immutable.

    Functions are stored as BinaryFunction objects with sparse CSR representations.
    Relations are dense tensors:
    - Unary relations: shape [1 + item_count]
    - Binary relations: shape [1 + item_count, 1 + item_count]
    """

    name: str
    item_count: int
    nullary_functions: Mapping[str, Ob]
    binary_functions: Mapping[str, BinaryFunction]
    symmetric_functions: Mapping[str, BinaryFunction]
    unary_relations: Mapping[str, torch.Tensor]
    binary_relations: Mapping[str, torch.Tensor]

    def assert_eq(self, other: "Structure") -> None:
        assert self.name == other.name
        assert self.item_count == other.item_count
        assert self.nullary_functions == other.nullary_functions

        assert set(self.binary_functions) == set(other.binary_functions)
        for name, func in self.binary_functions.items():
            assert name in other.binary_functions
            func.assert_eq(other.binary_functions[name])

        assert set(self.symmetric_functions) == set(other.symmetric_functions)
        for name, func in self.symmetric_functions.items():
            assert name in other.symmetric_functions
            func.assert_eq(other.symmetric_functions[name])

        assert set(self.unary_relations) == set(other.unary_relations)
        for name, rel in self.unary_relations.items():
            assert name in other.unary_relations
            assert_tensors_equal(rel, other.unary_relations[name])

        assert set(self.binary_relations) == set(other.binary_relations)
        for name, rel in self.binary_relations.items():
            assert name in other.binary_relations
            assert_tensors_equal(rel, other.binary_relations[name])

    @staticmethod
    def load(
        filename: str,
        *,
        relations: bool = False,
        backend: Literal["python", "cpp"] = "cpp",
    ) -> "Structure":
        """
        Load a structure from a protobuf file.
        """
        from .io import load_structure

        return load_structure(filename, relations=relations, backend=backend)
