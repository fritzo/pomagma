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
class BinaryFunctionTable:
    ptrs: torch.Tensor
    args: torch.Tensor


@dataclass(frozen=True, slots=True, eq=False)
class BinaryFunction:
    """
    A binary function in the structure.
    """

    name: str
    LRv: BinaryFunctionTable
    VLr: BinaryFunctionTable
    VRl: BinaryFunctionTable

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
