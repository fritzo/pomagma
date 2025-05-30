import logging
from typing import Iterable, TypeVar

import numpy as np
import torch
from google.protobuf.message import Message
from immutables import Map

import pomagma.atlas.structure_pb2 as pb2
from pomagma.io import blobstore
from pomagma.io.protobuf import InFile

from .structure import Ob, Structure

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


def load_unary_function_data(proto_func: pb2.UnaryFunction) -> torch.Tensor:
    """
    Load unary function data into COO format.
    Returns a tensor of shape [2, num_entries] where:
    - tensor[0, :] are the input indices
    - tensor[1, :] are the output values
    """
    # First pass: count entries
    num_entries = sum(
        count_ob_map_entries(chunk.map) for chunk in iter_chunks(proto_func)
    )
    result = torch.zeros((2, num_entries), dtype=torch.int32)
    idx = 0

    for chunk in iter_chunks(proto_func):
        keys, vals = load_ob_map(chunk.map)
        for key, val in zip(keys, vals):
            result[0, idx] = key
            result[1, idx] = val
            idx += 1

    assert idx == num_entries, f"Expected {num_entries} entries, got {idx}"
    return result


def count_binary_function_entries(proto_func: pb2.BinaryFunction) -> int:
    """Count the number of entries in a binary function."""
    return sum(
        count_ob_map_entries(row.rhs_val)
        for chunk in iter_chunks(proto_func)
        for row in chunk.rows
    )


def load_binary_function_data(proto_func: pb2.BinaryFunction) -> torch.Tensor:
    """
    Load binary function data into COO format.
    Returns a tensor of shape [3, num_entries] where:
    - tensor[0, :] are the first argument indices
    - tensor[1, :] are the second argument indices
    - tensor[2, :] are the output values
    """
    # First pass: count entries
    num_entries = count_binary_function_entries(proto_func)
    result = torch.zeros((3, num_entries), dtype=torch.int32)
    idx = 0

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                result[0, idx] = lhs
                result[1, idx] = rhs
                result[2, idx] = val
                idx += 1

    assert idx == num_entries, f"Expected {num_entries} entries, got {idx}"
    return result


def load_symmetric_function_data(proto_func: pb2.BinaryFunction) -> torch.Tensor:
    """
    Load symmetric function data into COO format.
    For symmetric functions, we duplicate off-diagonal elements.
    Returns a tensor of shape [3, num_entries] where:
    - tensor[0, :] are the first argument indices
    - tensor[1, :] are the second argument indices
    - tensor[2, :] are the output values
    """
    # First pass: count entries
    # Allocate double the base entries as an overestimate for symmetric duplicates
    base_entries = count_binary_function_entries(proto_func)
    max_entries = 2 * base_entries
    result = torch.zeros((3, max_entries), dtype=torch.int32)
    idx = 0

    for chunk in iter_chunks(proto_func):
        for row in chunk.rows:
            lhs = row.lhs
            keys, vals = load_ob_map(row.rhs_val)
            for rhs, val in zip(keys, vals):
                # Add the original entry
                result[0, idx] = lhs
                result[1, idx] = rhs
                result[2, idx] = val
                idx += 1

                # Add symmetric entry if different
                if lhs != rhs:
                    result[0, idx] = rhs
                    result[1, idx] = lhs
                    result[2, idx] = val
                    idx += 1

    # Trim to actual size used
    assert idx <= max_entries, f"Expected {max_entries} entries, got {idx}"
    if idx < max_entries:
        result = result[:, :idx]
    return result


def load_unary_relation_data(
    proto_rel: pb2.UnaryRelation, item_count: int
) -> torch.Tensor:
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


def load_binary_relation_data(
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
    injective_functions = {}
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
        logger.debug(f"Loading injective function: {proto_func.name}")
        tensor = load_unary_function_data(proto_func)
        injective_functions[proto_func.name] = tensor

    for proto_func in proto_structure.binary_functions:
        logger.debug(f"Loading binary function: {proto_func.name}")
        tensor = load_binary_function_data(proto_func)
        binary_functions[proto_func.name] = tensor

    for proto_func in proto_structure.symmetric_functions:
        logger.debug(f"Loading symmetric function: {proto_func.name}")
        tensor = load_symmetric_function_data(proto_func)
        symmetric_functions[proto_func.name] = tensor

    if relations:
        for proto_rel in proto_structure.unary_relations:
            logger.debug(f"Loading unary relation: {proto_rel.name}")
            tensor = load_unary_relation_data(proto_rel, item_count)
            unary_relations[proto_rel.name] = tensor

        for proto_rel in proto_structure.binary_relations:
            logger.debug(f"Loading binary relation: {proto_rel.name}")
            tensor = load_binary_relation_data(proto_rel, item_count)
            binary_relations[proto_rel.name] = tensor

    return Structure(
        name=name,
        item_count=item_count,
        nullary_functions=Map(nullary_functions),
        injective_functions=Map(injective_functions),
        binary_functions=Map(binary_functions),
        symmetric_functions=Map(symmetric_functions),
        unary_relations=Map(unary_relations),
        binary_relations=Map(binary_relations),
    )
