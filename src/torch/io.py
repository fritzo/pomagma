import logging
from typing import Iterable, TypeVar

import numpy as np
import torch
from google.protobuf.message import Message
from immutables import Map

import pomagma.atlas.structure_pb2 as pb2
from pomagma.io import blobstore
from pomagma.io.protobuf import InFile

from .structure import BinaryFunction, Ob, SparseTernaryRelation, Structure

logger = logging.getLogger(__name__)

_M = TypeVar("_M", bound=Message)


def delta_decompress(ob_map: pb2.ObMap) -> tuple[list[Ob], list[Ob]]:
    """
    Python implementation of delta decompression for ObMap.
    Equivalent to the C++ protobuf::delta_decompress function.
    """
    if len(ob_map.key_diff_minus_one) == 0:
        # Already uncompressed
        return list(ob_map.key), list(ob_map.val)

    assert len(ob_map.key_diff_minus_one) == len(ob_map.val_diff)

    keys = []
    vals = []
    key = 0
    val = 0

    for i in range(len(ob_map.key_diff_minus_one)):
        key += ob_map.key_diff_minus_one[i] + 1
        val += ob_map.val_diff[i]
        keys.append(key)
        vals.append(val)

    return keys, vals


def load_ob_map(ob_map: pb2.ObMap) -> tuple[Iterable[Ob], Iterable[Ob]]:
    """
    Load an ObMap from protobuf to Python lists.
    """
    if ob_map.key:
        return ob_map.key, ob_map.val
    return delta_decompress(ob_map)


def count_ob_map_entries(ob_map: pb2.ObMap) -> int:
    """Count the number of entries in an ObMap."""
    return len(ob_map.key) + len(ob_map.key_diff_minus_one)  # either dense or sparse


def load_dense_set(ob_set: pb2.ObSet, max_item: int) -> torch.Tensor:
    """
    Load a dense set from protobuf ObSet to PyTorch tensor.
    The dense field contains a bitset where each bit represents whether an item
    is in the set.
    """
    if not ob_set.dense:
        return torch.zeros(max_item + 1, dtype=torch.bool)

    # Convert bytes to numpy array of uint8, then to bits
    byte_data = np.frombuffer(ob_set.dense, dtype=np.uint8)

    # Unpack bits (LSB first)
    bits = np.unpackbits(byte_data, bitorder="little")

    # Truncate or pad to max_item + 1
    if len(bits) > max_item + 1:
        bits = bits[: max_item + 1]
    elif len(bits) < max_item + 1:
        bits = np.pad(
            bits, (0, max_item + 1 - len(bits)), "constant", constant_values=0
        )

    return torch.from_numpy(bits.astype(bool))


def iter_chunks(message: _M) -> Iterable[_M]:
    """
    Iterate over the main message and all chunks from blobs.
    Equivalent to the C++ BlobReader functionality.
    """
    # Yield the main message
    yield message

    # Yield chunks from blobs
    for hexdigest in message.blobs:
        blob_path = blobstore.find_blob(hexdigest)
        with InFile(blob_path) as f:
            chunk = type(message)()
            f.read(chunk)
            yield chunk
            assert not chunk.blobs


def count_binary_function_entries(proto_func: pb2.BinaryFunction) -> int:
    """Count the number of entries in a binary function."""
    return sum(
        count_ob_map_entries(row.rhs_val)
        for chunk in iter_chunks(proto_func)
        for row in chunk.rows
    )


def load_binary_function(
    proto_func: pb2.BinaryFunction, item_count: int
) -> BinaryFunction:
    """
    Load binary function data into a BinaryFunction object.
    """
    # Pass 1: Count entries for each table
    LRv_counts = [0] * (item_count + 1)  # indexed by val
    VLr_counts = [0] * (item_count + 1)  # indexed by rhs
    VRl_counts = [0] * (item_count + 1)  # indexed by lhs

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                LRv_counts[val] += 1
                VLr_counts[rhs] += 1
                VRl_counts[lhs] += 1

    # Create pointers from counts
    def create_ptrs_from_counts(counts: list[int]) -> torch.Tensor:
        ptrs = torch.zeros(len(counts) + 1, dtype=torch.int32)
        for i in range(len(counts)):
            ptrs[i + 1] = ptrs[i] + counts[i]
        return ptrs

    LRv_ptrs = create_ptrs_from_counts(LRv_counts)
    VLr_ptrs = create_ptrs_from_counts(VLr_counts)
    VRl_ptrs = create_ptrs_from_counts(VRl_counts)

    # Allocate args tensors
    LRv_nnz = int(LRv_ptrs[-1].item())
    VLr_nnz = int(VLr_ptrs[-1].item())
    VRl_nnz = int(VRl_ptrs[-1].item())

    LRv_args = torch.zeros((LRv_nnz, 2), dtype=torch.int32)
    VLr_args = torch.zeros((VLr_nnz, 2), dtype=torch.int32)
    VRl_args = torch.zeros((VRl_nnz, 2), dtype=torch.int32)

    # Pass 2: Load data with position tracking
    LRv_pos = [0] * (item_count + 1)
    VLr_pos = [0] * (item_count + 1)
    VRl_pos = [0] * (item_count + 1)

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                # LRv table: indexed by val, stores (lhs, rhs)
                idx = LRv_ptrs[val] + LRv_pos[val]
                LRv_args[idx, 0] = lhs
                LRv_args[idx, 1] = rhs
                LRv_pos[val] += 1

                # VLr table: indexed by rhs, stores (val, lhs)
                idx = VLr_ptrs[rhs] + VLr_pos[rhs]
                VLr_args[idx, 0] = val
                VLr_args[idx, 1] = lhs
                VLr_pos[rhs] += 1

                # VRl table: indexed by lhs, stores (val, rhs)
                idx = VRl_ptrs[lhs] + VRl_pos[lhs]
                VRl_args[idx, 0] = val
                VRl_args[idx, 1] = rhs
                VRl_pos[lhs] += 1

    # Verify that positions match counts
    assert LRv_pos == LRv_counts, f"LRv position mismatch: {LRv_pos} != {LRv_counts}"
    assert VLr_pos == VLr_counts, f"VLr position mismatch: {VLr_pos} != {VLr_counts}"
    assert VRl_pos == VRl_counts, f"VRl position mismatch: {VRl_pos} != {VRl_counts}"

    # Create BinaryFunctionTable objects
    LRv = SparseTernaryRelation(ptrs=LRv_ptrs, args=LRv_args)
    VLr = SparseTernaryRelation(ptrs=VLr_ptrs, args=VLr_args)
    VRl = SparseTernaryRelation(ptrs=VRl_ptrs, args=VRl_args)

    return BinaryFunction(name=proto_func.name, LRv=LRv, VLr=VLr, VRl=VRl)


def load_symmetric_function(
    proto_func: pb2.BinaryFunction, item_count: int
) -> BinaryFunction:
    """
    Load symmetric function data into a BinaryFunction object.
    For symmetric functions, we duplicate off-diagonal elements.
    """
    # Pass 1: Count entries for each table, including symmetric duplicates
    LRv_counts = [0] * (item_count + 1)  # indexed by val
    VLr_counts = [0] * (item_count + 1)  # indexed by rhs
    VRl_counts = [0] * (item_count + 1)  # indexed by lhs

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                # Original entry
                LRv_counts[val] += 1
                VLr_counts[rhs] += 1
                VRl_counts[lhs] += 1

                # Symmetric entry (if different)
                if lhs != rhs:
                    LRv_counts[val] += (
                        1  # Same val, but (rhs, lhs) instead of (lhs, rhs)
                    )
                    VLr_counts[lhs] += 1  # Now indexed by lhs, stores (val, rhs)
                    VRl_counts[rhs] += 1  # Now indexed by rhs, stores (val, lhs)

    # Create pointers from counts
    def create_ptrs_from_counts(counts: list[int]) -> torch.Tensor:
        ptrs = torch.zeros(len(counts) + 1, dtype=torch.int32)
        for i in range(len(counts)):
            ptrs[i + 1] = ptrs[i] + counts[i]
        return ptrs

    LRv_ptrs = create_ptrs_from_counts(LRv_counts)
    VLr_ptrs = create_ptrs_from_counts(VLr_counts)
    VRl_ptrs = create_ptrs_from_counts(VRl_counts)

    # Allocate args tensors
    LRv_nnz = int(LRv_ptrs[-1].item())
    VLr_nnz = int(VLr_ptrs[-1].item())
    VRl_nnz = int(VRl_ptrs[-1].item())

    LRv_args = torch.zeros((LRv_nnz, 2), dtype=torch.int32)
    VLr_args = torch.zeros((VLr_nnz, 2), dtype=torch.int32)
    VRl_args = torch.zeros((VRl_nnz, 2), dtype=torch.int32)

    # Pass 2: Load data with position tracking, including symmetric duplicates
    LRv_pos = [0] * (item_count + 1)
    VLr_pos = [0] * (item_count + 1)
    VRl_pos = [0] * (item_count + 1)

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                # Original entry: (lhs, rhs, val)
                # LRv table: indexed by val, stores (lhs, rhs)
                idx = LRv_ptrs[val] + LRv_pos[val]
                LRv_args[idx, 0] = lhs
                LRv_args[idx, 1] = rhs
                LRv_pos[val] += 1

                # VLr table: indexed by rhs, stores (val, lhs)
                idx = VLr_ptrs[rhs] + VLr_pos[rhs]
                VLr_args[idx, 0] = val
                VLr_args[idx, 1] = lhs
                VLr_pos[rhs] += 1

                # VRl table: indexed by lhs, stores (val, rhs)
                idx = VRl_ptrs[lhs] + VRl_pos[lhs]
                VRl_args[idx, 0] = val
                VRl_args[idx, 1] = rhs
                VRl_pos[lhs] += 1

                # Symmetric entry: (rhs, lhs, val) if lhs != rhs
                if lhs == rhs:
                    continue

                # LRv table: indexed by val, stores (rhs, lhs)
                idx = LRv_ptrs[val] + LRv_pos[val]
                LRv_args[idx, 0] = rhs
                LRv_args[idx, 1] = lhs
                LRv_pos[val] += 1

                # VLr table: indexed by lhs (now the rhs), stores (val, rhs)
                idx = VLr_ptrs[lhs] + VLr_pos[lhs]
                VLr_args[idx, 0] = val
                VLr_args[idx, 1] = rhs
                VLr_pos[lhs] += 1

                # VRl table: indexed by rhs (now the lhs), stores (val, lhs)
                idx = VRl_ptrs[rhs] + VRl_pos[rhs]
                VRl_args[idx, 0] = val
                VRl_args[idx, 1] = lhs
                VRl_pos[rhs] += 1

    # Verify that positions match counts
    assert LRv_pos == LRv_counts
    assert VLr_pos == VLr_counts
    assert VRl_pos == VRl_counts

    # Create SparseTernaryRelation objects
    LRv = SparseTernaryRelation(ptrs=LRv_ptrs, args=LRv_args)
    VLr = SparseTernaryRelation(ptrs=VLr_ptrs, args=VLr_args)
    VRl = SparseTernaryRelation(ptrs=VRl_ptrs, args=VRl_args)

    return BinaryFunction(name=proto_func.name, LRv=LRv, VLr=VLr, VRl=VRl)


def load_unary_relation(proto_rel: pb2.UnaryRelation, item_count: int) -> torch.Tensor:
    """
    Load unary relation data into a PyTorch tensor.
    Returns a boolean tensor of shape [1 + item_count].
    """
    result = torch.zeros(1 + item_count, dtype=torch.bool)

    for chunk in iter_chunks(proto_rel):
        if chunk.set.dense:
            dense_set = load_dense_set(chunk.set, item_count)
            result = result | dense_set

    return result


def load_binary_relation(
    proto_rel: pb2.BinaryRelation, item_count: int
) -> torch.Tensor:
    """
    Load binary relation data into a PyTorch tensor.
    Returns a boolean tensor of shape [1 + item_count, 1 + item_count].
    """
    result = torch.zeros(1 + item_count, 1 + item_count, dtype=torch.bool)

    for chunk in iter_chunks(proto_rel):
        for row in chunk.rows:
            lhs = row.lhs
            rhs_set = load_dense_set(row.rhs, item_count)
            result[lhs] = result[lhs] | rhs_set

    return result


def load_structure(filename: str, *, relations: bool = False) -> Structure:
    """
    Load a structure from a protobuf file.

    Args:
        filename: Path to the .pb file.
        relations: Whether to load relation data. Default: False.
    """
    proto_structure = pb2.Structure()
    with InFile(blobstore.find_blob(blobstore.load_blob_ref(filename))) as f:
        f.read(proto_structure)

    name = proto_structure.name
    item_count = proto_structure.carrier.item_count
    nullary_functions = {}
    binary_functions = {}
    symmetric_functions = {}
    unary_relations = {}
    binary_relations = {}

    constants = " ".join(
        sorted(proto_func.name for proto_func in proto_structure.nullary_functions)
    )
    logger.debug(f"Loading constants: {constants}")
    for proto_func in proto_structure.nullary_functions:
        nullary_functions[proto_func.name] = proto_func.val

    for proto_func in proto_structure.injective_functions:
        raise NotImplementedError("Injective functions are not supported yet.")

    for proto_func in proto_structure.binary_functions:
        logger.debug(f"Loading binary function: {proto_func.name}")
        binary_functions[proto_func.name] = load_binary_function(proto_func, item_count)

    for proto_func in proto_structure.symmetric_functions:
        logger.debug(f"Loading symmetric function: {proto_func.name}")
        symmetric_functions[proto_func.name] = load_symmetric_function(
            proto_func, item_count
        )

    if relations:
        for proto_rel in proto_structure.unary_relations:
            logger.debug(f"Loading unary relation: {proto_rel.name}")
            unary_relations[proto_rel.name] = load_unary_relation(proto_rel, item_count)

        for proto_rel in proto_structure.binary_relations:
            logger.debug(f"Loading binary relation: {proto_rel.name}")
            binary_relations[proto_rel.name] = load_binary_relation(
                proto_rel, item_count
            )

    return Structure(
        name=name,
        item_count=item_count,
        nullary_functions=Map(nullary_functions),
        binary_functions=Map(binary_functions),
        symmetric_functions=Map(symmetric_functions),
        unary_relations=Map(unary_relations),
        binary_relations=Map(binary_relations),
    )
