from dataclasses import dataclass
from typing import Mapping, NewType

import torch

Ob = NewType("Ob", int)
"""An item in the carrier. 1-indexed, so 0 means undefined."""


class BinaryFunctionSumProduct(torch.autograd.Function):
    @staticmethod
    def forward(
        ctx,
        LRv_ptrs: torch.Tensor,
        LRv_args: torch.Tensor,
        VLr_ptrs: torch.Tensor,
        VLr_args: torch.Tensor,
        VRl_ptrs: torch.Tensor,
        VRl_args: torch.Tensor,
        lhs: torch.Tensor,
        rhs: torch.Tensor,
    ) -> torch.Tensor:
        val = torch.ops.pomagma.binary_function_sum_product(
            LRv_ptrs, LRv_args, lhs, rhs
        )
        ctx.save_for_backward(VLr_ptrs, VLr_args, VRl_ptrs, VRl_args, lhs, rhs)
        return val

    @staticmethod
    def backward(ctx, grad_val: torch.Tensor) -> tuple[torch.Tensor, ...]:
        VLr_ptrs, VLr_args, VRl_ptrs, VRl_args, lhs, rhs = ctx.saved_tensors
        grad_lhs = torch.ops.pomagma.binary_function_sum_product(
            VRl_ptrs, VRl_args, grad_val, rhs
        )
        grad_rhs = torch.ops.pomagma.binary_function_sum_product(
            VLr_ptrs, VLr_args, grad_val, lhs
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

    def __init__(self, num_entries: int) -> None:
        optimal_size = 2 ** (num_entries.bit_length() + 1)
        hash_table = torch.zeros(optimal_size, 3, dtype=torch.int32)
        object.__setattr__(self, "hash_table", hash_table)

    def __getitem__(self, key: tuple[Ob, Ob]) -> Ob:
        lhs, rhs = key
        H = self.hash_table.size(0)
        h = hash((lhs, rhs)) % H
        while self.hash_table[h, 0] != lhs or self.hash_table[h, 1] != rhs:
            if self.hash_table[h, 0] == 0:
                return Ob(0)
            h = (h + 1) % H
        return int(self.hash_table[h, 2])

    def __setitem__(self, key: tuple[Ob, Ob], val: Ob) -> None:
        lhs, rhs = key
        H = self.hash_table.size(0)
        h = hash((lhs, rhs)) % H
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


@dataclass(frozen=True, slots=True, eq=False)
class BinaryFunction:
    """
    A binary function in the structure with support for automatic differentiation.

    Stores the function f(L, R) = V in four different sparse representations:
    - func: Maps (Left, Right) -> Value for lookup
    - LRv: Maps Value -> (Left, Right) pairs for forward evaluation
    - VLr: Maps Right -> (Value, Left) pairs for backward wrt right
    - VRl: Maps Left -> (Value, Right) pairs for backward wrt left

    These three tables enable efficient forward and backward passes in autograd.
    """

    name: str
    func: SparseBinaryFunction  # (Left, Right) -> Value mapping for lookup
    LRv: SparseTernaryRelation  # Value -> (Left, Right) pairs for forward pass
    VLr: SparseTernaryRelation  # Right -> (Value, Left) pairs for backward wrt right
    VRl: SparseTernaryRelation  # Left -> (Value, Right) pairs for backward wrt left

    def __getitem__(self, key: tuple[Ob, Ob]) -> Ob:
        """Lookup the value of the function at the given (lhs, rhs) pair."""
        return self.func[key]

    def sum_product(self, lhs: torch.Tensor, rhs: torch.Tensor) -> torch.Tensor:
        """Differentiably convolve two weight vectors."""
        return BinaryFunctionSumProduct.apply(
            self.LRv.ptrs,
            self.LRv.args,
            self.VLr.ptrs,
            self.VLr.args,
            self.VRl.ptrs,
            self.VRl.args,
            lhs,
            rhs,
        )

    @torch.no_grad()
    def max_product(self, lhs: torch.Tensor, rhs: torch.Tensor) -> torch.Tensor:
        """Non-differentiably max-convolve two weight vectors."""
        return torch.ops.pomagma.binary_function_max_product(
            self.LRv.ptrs, self.LRv.args, lhs, rhs
        )


@dataclass(frozen=True, slots=True, eq=False)
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

    @staticmethod
    def load(filename: str, *, relations: bool = False) -> "Structure":
        """
        Load a structure from a protobuf file.
        """
        from .io import load_structure

        return load_structure(filename, relations=relations)
