import logging
from collections.abc import Iterable
from typing import Literal, TypeVar

import numpy as np
import torch
from google.protobuf.message import Message
from immutables import Map

import pomagma.atlas.structure_pb2 as pb2
from pomagma.io import blobstore
from pomagma.io.protobuf import InFile

from .structure import (
    BinaryFunction,
    Ob,
    SparseBinaryFunction,
    SparseTernaryRelation,
    Structure,
)

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
    func_entries = 0
    Vlr_counts = [0] * (item_count + 1)  # indexed by val
    Rvl_counts = [0] * (item_count + 1)  # indexed by rhs
    Lvr_counts = [0] * (item_count + 1)  # indexed by lhs

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                func_entries += 1
                Vlr_counts[val] += 1
                Rvl_counts[rhs] += 1
                Lvr_counts[lhs] += 1

    # Create pointers from counts
    def create_ptrs_from_counts(counts: list[int]) -> torch.Tensor:
        ptrs = torch.zeros(len(counts) + 1, dtype=torch.int32)
        for i in range(len(counts)):
            ptrs[i + 1] = ptrs[i] + counts[i]
        return ptrs

    Vlr_ptrs = create_ptrs_from_counts(Vlr_counts)
    Rvl_ptrs = create_ptrs_from_counts(Rvl_counts)
    Lvr_ptrs = create_ptrs_from_counts(Lvr_counts)

    # Allocate tensors
    LRv = SparseBinaryFunction(func_entries)
    Vlr_nnz = int(Vlr_ptrs[-1].item())
    Rvl_nnz = int(Rvl_ptrs[-1].item())
    Lvr_nnz = int(Lvr_ptrs[-1].item())

    Vlr_args = torch.zeros((Vlr_nnz, 2), dtype=torch.int32)
    Rvl_args = torch.zeros((Rvl_nnz, 2), dtype=torch.int32)
    Lvr_args = torch.zeros((Lvr_nnz, 2), dtype=torch.int32)

    # Pass 2: Load data with position tracking
    Vlr_pos = [0] * (item_count + 1)
    Rvl_pos = [0] * (item_count + 1)
    Lvr_pos = [0] * (item_count + 1)

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                LRv[lhs, rhs] = val

                # Vlr table: indexed by val, stores (lhs, rhs)
                idx = Vlr_ptrs[val] + Vlr_pos[val]
                Vlr_args[idx, 0] = lhs
                Vlr_args[idx, 1] = rhs
                Vlr_pos[val] += 1

                # Rvl table: indexed by rhs, stores (val, lhs)
                idx = Rvl_ptrs[rhs] + Rvl_pos[rhs]
                Rvl_args[idx, 0] = val
                Rvl_args[idx, 1] = lhs
                Rvl_pos[rhs] += 1

                # Lvr table: indexed by lhs, stores (val, rhs)
                idx = Lvr_ptrs[lhs] + Lvr_pos[lhs]
                Lvr_args[idx, 0] = val
                Lvr_args[idx, 1] = rhs
                Lvr_pos[lhs] += 1

    # Verify that positions match counts
    assert Vlr_pos == Vlr_counts, f"Vlr position mismatch: {Vlr_pos} != {Vlr_counts}"
    assert Rvl_pos == Rvl_counts, f"Rvl position mismatch: {Rvl_pos} != {Rvl_counts}"
    assert Lvr_pos == Lvr_counts, f"Lvr position mismatch: {Lvr_pos} != {Lvr_counts}"

    # Create BinaryFunctionTable objects
    Vlr = SparseTernaryRelation(ptrs=Vlr_ptrs, args=Vlr_args)
    Rvl = SparseTernaryRelation(ptrs=Rvl_ptrs, args=Rvl_args)
    Lvr = SparseTernaryRelation(ptrs=Lvr_ptrs, args=Lvr_args)

    return BinaryFunction(name=proto_func.name, LRv=LRv, Vlr=Vlr, Rvl=Rvl, Lvr=Lvr)


def load_symmetric_function(
    proto_func: pb2.BinaryFunction, item_count: int
) -> BinaryFunction:
    """
    Load symmetric function data into a BinaryFunction object.
    For symmetric functions, we duplicate off-diagonal elements.
    """
    # Pass 1: Count entries for each table, including symmetric duplicates
    func_entries = 0
    Vlr_counts = [0] * (item_count + 1)  # indexed by val
    Rvl_counts = [0] * (item_count + 1)  # indexed by rhs
    Lvr_counts = [0] * (item_count + 1)  # indexed by lhs

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                # Original entry
                func_entries += 1
                Vlr_counts[val] += 1
                Rvl_counts[rhs] += 1
                Lvr_counts[lhs] += 1

                # Symmetric entry (if different)
                if lhs == rhs:
                    continue
                func_entries += 1
                Vlr_counts[val] += 1  # Same val, but (rhs, lhs) instead of (lhs, rhs)
                Rvl_counts[lhs] += 1  # Now indexed by lhs, stores (val, rhs)
                Lvr_counts[rhs] += 1  # Now indexed by rhs, stores (val, lhs)

    # Create pointers from counts
    def create_ptrs_from_counts(counts: list[int]) -> torch.Tensor:
        ptrs = torch.zeros(len(counts) + 1, dtype=torch.int32)
        for i in range(len(counts)):
            ptrs[i + 1] = ptrs[i] + counts[i]
        return ptrs

    Vlr_ptrs = create_ptrs_from_counts(Vlr_counts)
    Rvl_ptrs = create_ptrs_from_counts(Rvl_counts)
    Lvr_ptrs = create_ptrs_from_counts(Lvr_counts)

    # Allocate tensors
    func = SparseBinaryFunction(func_entries)
    Vlr_nnz = int(Vlr_ptrs[-1].item())
    Rvl_nnz = int(Rvl_ptrs[-1].item())
    Lvr_nnz = int(Lvr_ptrs[-1].item())

    Vlr_args = torch.zeros((Vlr_nnz, 2), dtype=torch.int32)
    Rvl_args = torch.zeros((Rvl_nnz, 2), dtype=torch.int32)
    Lvr_args = torch.zeros((Lvr_nnz, 2), dtype=torch.int32)

    # Pass 2: Load data with position tracking, including symmetric duplicates
    Vlr_pos = [0] * (item_count + 1)
    Rvl_pos = [0] * (item_count + 1)
    Lvr_pos = [0] * (item_count + 1)

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                # Original entry: (lhs, rhs, val)
                func[lhs, rhs] = val

                # Vlr table: indexed by val, stores (lhs, rhs)
                idx = Vlr_ptrs[val] + Vlr_pos[val]
                Vlr_args[idx, 0] = lhs
                Vlr_args[idx, 1] = rhs
                Vlr_pos[val] += 1

                # Rvl table: indexed by rhs, stores (val, lhs)
                idx = Rvl_ptrs[rhs] + Rvl_pos[rhs]
                Rvl_args[idx, 0] = val
                Rvl_args[idx, 1] = lhs
                Rvl_pos[rhs] += 1

                # Lvr table: indexed by lhs, stores (val, rhs)
                idx = Lvr_ptrs[lhs] + Lvr_pos[lhs]
                Lvr_args[idx, 0] = val
                Lvr_args[idx, 1] = rhs
                Lvr_pos[lhs] += 1

                # Symmetric entry: (rhs, lhs, val) if lhs != rhs
                if lhs == rhs:
                    continue
                func[rhs, lhs] = val

                # Vlr table: indexed by val, stores (rhs, lhs)
                idx = Vlr_ptrs[val] + Vlr_pos[val]
                Vlr_args[idx, 0] = rhs
                Vlr_args[idx, 1] = lhs
                Vlr_pos[val] += 1

                # Rvl table: indexed by lhs (now the rhs), stores (val, rhs)
                idx = Rvl_ptrs[lhs] + Rvl_pos[lhs]
                Rvl_args[idx, 0] = val
                Rvl_args[idx, 1] = rhs
                Rvl_pos[lhs] += 1

                # Lvr table: indexed by rhs (now the lhs), stores (val, lhs)
                idx = Lvr_ptrs[rhs] + Lvr_pos[rhs]
                Lvr_args[idx, 0] = val
                Lvr_args[idx, 1] = lhs
                Lvr_pos[rhs] += 1

    # Verify that positions match counts
    assert Vlr_pos == Vlr_counts
    assert Rvl_pos == Rvl_counts
    assert Lvr_pos == Lvr_counts

    # Create SparseTernaryRelation objects
    Vlr = SparseTernaryRelation(ptrs=Vlr_ptrs, args=Vlr_args)
    Rvl = SparseTernaryRelation(ptrs=Rvl_ptrs, args=Rvl_args)
    Lvr = SparseTernaryRelation(ptrs=Lvr_ptrs, args=Lvr_args)

    return BinaryFunction(name=proto_func.name, LRv=func, Vlr=Vlr, Rvl=Rvl, Lvr=Lvr)


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


def load_structure(
    filename: str,
    *,
    relations: bool = False,
    backend: Literal["python", "cpp"] = "cpp",
) -> Structure:
    if backend == "python":
        return load_structure_py(filename, relations=relations)
    if backend == "cpp":
        return load_structure_cpp(filename, relations=relations)
    raise ValueError(f"Invalid backend: {backend}")


def load_structure_py(filename: str, *, relations: bool = False) -> Structure:
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
    logger.debug("Loading constants: %s", constants)
    for proto_func in proto_structure.nullary_functions:
        nullary_functions[proto_func.name] = proto_func.val

    for proto_func in proto_structure.injective_functions:
        raise NotImplementedError("Injective functions are not supported yet.")

    for proto_func in proto_structure.binary_functions:
        logger.debug("Loading binary function: %s", proto_func.name)
        binary_functions[proto_func.name] = load_binary_function(proto_func, item_count)

    for proto_func in proto_structure.symmetric_functions:
        logger.debug("Loading symmetric function: %s", proto_func.name)
        symmetric_functions[proto_func.name] = load_symmetric_function(
            proto_func, item_count
        )

    if relations:
        for proto_rel in proto_structure.unary_relations:
            logger.debug("Loading unary relation: %s", proto_rel.name)
            unary_relations[proto_rel.name] = load_unary_relation(proto_rel, item_count)

        for proto_rel in proto_structure.binary_relations:
            logger.debug("Loading binary relation: %s", proto_rel.name)
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


def load_structure_cpp(filename: str, *, relations: bool = False) -> Structure:
    """
    Load a structure from a protobuf file using C++ implementation.

    Args:
        filename: Path to the .pb file.
        relations: Whether to load relation data. Default: False.
    """
    # Resolve blob path once for both C++ and Python usage
    resolved_blob_path = blobstore.find_blob(blobstore.load_blob_ref(filename))

    # Load tensors indexed by fully qualified names
    keys: list[str]
    values: list[torch.Tensor]
    cpp_relations = False  # TODO: Implement relations in C++
    keys, values = torch.ops.pomagma.load_structure(resolved_blob_path, cpp_relations)
    tensors = dict(zip(keys, values))

    # Fall back to Python proto loading for structure name and relations
    proto_structure = pb2.Structure()
    with InFile(resolved_blob_path) as f:
        f.read(proto_structure)

    name = proto_structure.name
    item_count = tensors["item_count"].item()
    assert isinstance(item_count, int)

    # Parse nullary functions
    nullary_functions: dict[str, Ob] = {}
    for key, tensor in tensors.items():
        if key.startswith("nullary_functions."):
            func_name = key[len("nullary_functions.") :]
            nullary_functions[func_name] = Ob(int(tensor.item()))

    # Helper function to parse binary/symmetric functions
    def parse_functions(prefix: str, target_dict: dict):
        """Parse binary or symmetric functions from tensors."""
        func_keys = {
            parts[1]
            for key in tensors
            if key.startswith(prefix)
            if len(parts := key.split(".")) >= 3
        }

        for func_name in func_keys:
            func_prefix = f"{prefix}{func_name}"

            # Get LRv hash table and pass directly to SparseBinaryFunction
            LRv = SparseBinaryFunction(hash_table=tensors[f"{func_prefix}.LRv"])

            # Create SparseTernaryRelation objects
            Vlr = SparseTernaryRelation(
                ptrs=tensors[f"{func_prefix}.Vlr.ptrs"],
                args=tensors[f"{func_prefix}.Vlr.args"],
            )
            Rvl = SparseTernaryRelation(
                ptrs=tensors[f"{func_prefix}.Rvl.ptrs"],
                args=tensors[f"{func_prefix}.Rvl.args"],
            )
            Lvr = SparseTernaryRelation(
                ptrs=tensors[f"{func_prefix}.Lvr.ptrs"],
                args=tensors[f"{func_prefix}.Lvr.args"],
            )

            target_dict[func_name] = BinaryFunction(
                name=func_name, LRv=LRv, Vlr=Vlr, Rvl=Rvl, Lvr=Lvr
            )

    # Parse binary functions
    binary_functions: dict[str, BinaryFunction] = {}
    parse_functions("binary_functions.", binary_functions)

    # Parse symmetric functions
    symmetric_functions: dict[str, BinaryFunction] = {}
    parse_functions("symmetric_functions.", symmetric_functions)

    # Parse relations
    unary_relations: dict[str, torch.Tensor] = {}
    binary_relations: dict[str, torch.Tensor] = {}
    if relations:
        # Fall back to Python proto loading for relations
        for proto_rel in proto_structure.unary_relations:
            logger.debug("Loading unary relation: %s", proto_rel.name)
            unary_relations[proto_rel.name] = load_unary_relation(proto_rel, item_count)

        for proto_rel in proto_structure.binary_relations:
            logger.debug("Loading binary relation: %s", proto_rel.name)
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
