from dataclasses import dataclass
from typing import Mapping, NewType

import torch

from .language import Language

Ob = NewType("Ob", int)
"""An item in the carrier. 1-indexed, so 0 means undefined."""


class TorchBinaryFunction(torch.autograd.Function):
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
        val = torch.ops.pomagma.binary_function(LRv_ptrs, LRv_args, lhs, rhs)
        ctx.save_for_backward(VLr_ptrs, VLr_args, VRl_ptrs, VRl_args, lhs, rhs)
        return val

    @staticmethod
    def backward(ctx, grad_val: torch.Tensor) -> tuple[torch.Tensor, ...]:
        VLr_ptrs, VLr_args, VRl_ptrs, VRl_args, lhs, rhs = ctx.saved_tensors
        grad_lhs = torch.ops.pomagma.binary_function(VRl_ptrs, VRl_args, grad_val, rhs)
        grad_rhs = torch.ops.pomagma.binary_function(VLr_ptrs, VLr_args, grad_val, lhs)
        return (None, None, None, None, None, None, grad_lhs, grad_rhs)


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

    Stores the function f(L, R) = V in three different sparse representations:
    - LRv: Maps (Left, Right) -> Value for forward evaluation
    - VLr: Maps (Value, Left) -> Right for backward differentiation wrt right argument
    - VRl: Maps (Value, Right) -> Left for backward differentiation wrt left argument

    These three tables enable efficient forward and backward passes in autograd.
    """

    name: str
    LRv: SparseTernaryRelation  # (Left, Right) -> Value mapping for forward pass
    VLr: SparseTernaryRelation  # (Value, Left) -> Right mapping for right gradient
    VRl: SparseTernaryRelation  # (Value, Right) -> Left mapping for left gradient

    def __call__(self, lhs: torch.Tensor, rhs: torch.Tensor) -> torch.Tensor:
        return TorchBinaryFunction.apply(
            self.LRv.ptrs,
            self.LRv.args,
            self.VLr.ptrs,
            self.VLr.args,
            self.VRl.ptrs,
            self.VRl.args,
            lhs,
            rhs,
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

    def propagate_complexity(
        self, language: Language, *, tol: float = 1e-6
    ) -> torch.Tensor:
        assert 0.0 < tol < 1.0
        # Initialize with atoms.
        probs = language.nullary_functions / language.nullary_functions.sum()

        # Propagate until convergence.
        diff = 1.0
        while diff > tol:
            prev = probs
            probs = self._propagate_complexity_step(language, probs)
            with torch.no_grad():
                diff = (probs - prev).abs().sum().item()

        return probs

    def _propagate_complexity_step(
        self, language: Language, probs: torch.Tensor
    ) -> torch.Tensor:
        out = language.nullary_functions.clone()
        for name, weight in language.binary_functions.items():
            out += weight * self.binary_functions[name](probs, probs)
        for name, weight in language.symmetric_functions.items():
            out += weight * self.symmetric_functions[name](probs, probs)
        return out
