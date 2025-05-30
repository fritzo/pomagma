from dataclasses import dataclass
from typing import Mapping, NewType

import torch

Ob = NewType("Ob", int)
"""An item in the carrier. 1-indexed, so 0 means undefined."""


class TorchBinaryFunction(torch.autograd.Function):
    @staticmethod
    def forward(
        ctx,
        LRv_ptrs: torch.Tensor,
        LRv_args: torch.Tensor,
        LVr_ptrs: torch.Tensor,
        LVr_args: torch.Tensor,
        RVl_ptrs: torch.Tensor,
        RVl_args: torch.Tensor,
        lhs: torch.Tensor,
        rhs: torch.Tensor,
    ) -> torch.Tensor:
        val = torch.ops.pomagma.binary_function(LRv_ptrs, LRv_args, lhs, rhs)
        ctx.save_for_backward(LVr_ptrs, LVr_args, RVl_ptrs, RVl_args, lhs, rhs)
        return val

    @staticmethod
    def backward(ctx, grad_val: torch.Tensor) -> tuple[torch.Tensor, ...]:
        LVr_ptrs, LVr_args, RVl_ptrs, RVl_args, lhs, rhs = ctx.saved_tensors
        grad_lhs = torch.ops.pomagma.binary_function(LVr_ptrs, LVr_args, grad_val, rhs)
        grad_rhs = torch.ops.pomagma.binary_function(RVl_ptrs, RVl_args, grad_val, lhs)
        return (None, None, None, None, None, None, grad_lhs, grad_rhs)


@dataclass(frozen=True, slots=True, eq=False)
class BinaryFunctionDirection:
    ptrs: torch.Tensor
    args: torch.Tensor


@dataclass(frozen=True, slots=True, eq=False)
class BinaryFunction:
    """
    A binary function in the structure.
    """

    name: str
    LRv: BinaryFunctionDirection
    LVr: BinaryFunctionDirection
    RVl: BinaryFunctionDirection

    def __call__(self, lhs: torch.Tensor, rhs: torch.Tensor) -> torch.Tensor:
        return TorchBinaryFunction.apply(
            self.LRv.ptrs,
            self.LRv.args,
            self.LVr.ptrs,
            self.LVr.args,
            self.RVl.ptrs,
            self.RVl.args,
            lhs,
            rhs,
        )


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
