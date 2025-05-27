import logging
from dataclasses import dataclass
from typing import Mapping, NewType

import numpy as np
from immutables import Map

import torch

# Import the protobuf structures
from pomagma.atlas.structure_pb2 import Structure as ProtoStructure
from pomagma.io import blobstore
from pomagma.io.protobuf import InFile

logger = logging.getLogger(__name__)

Ob = NewType("Ob", int)


def delta_decompress(ob_map) -> tuple[list[Ob], list[Ob]]:
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


def load_dense_set(ob_set, max_item: int) -> torch.Tensor:
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


def load_blob_chunks(hexdigest, message_type):
    """
    Load and parse chunks from a blob file.
    Equivalent to the C++ BlobReader functionality.
    """
    # Convert bytes to string if necessary
    if isinstance(hexdigest, bytes):
        hexdigest = hexdigest.decode("utf-8")

    blob_path = blobstore.find_blob(hexdigest)
    chunks = []

    try:
        with InFile(blob_path) as f:
            while True:
                try:
                    chunk = message_type()
                    # Try to read a chunk - this is a simplified version
                    # In the C++ version, this uses try_read_chunk which parses
                    # individual fields.  For simplicity, we'll assume each blob
                    # contains a single message.
                    f.read(chunk)
                    chunks.append(chunk)
                    break  # For now, assume one message per blob
                except Exception:
                    break
    except Exception as e:
        print(f"Warning: Could not load blob {hexdigest}: {e}")

    return chunks


def load_injective_function_data(proto_func, item_count: int) -> torch.Tensor:
    """
    Load injective function data into a PyTorch tensor.
    Returns a tensor of shape [1 + item_count] where tensor[i] = f(i) or 0 if undefined.
    """
    result = torch.zeros(1 + item_count, dtype=torch.int32)

    # Load data from the main message
    if proto_func.map.key:
        keys, vals = delta_decompress(proto_func.map)
        for key, val in zip(keys, vals):
            if key <= item_count:
                result[key] = val

    # Load data from blobs
    for hexdigest in proto_func.blobs:
        from pomagma.atlas.structure_pb2 import UnaryFunction

        chunks = load_blob_chunks(hexdigest, UnaryFunction)
        for chunk in chunks:
            if chunk.map.key:
                keys, vals = delta_decompress(chunk.map)
                for key, val in zip(keys, vals):
                    if key <= item_count:
                        result[key] = val

    return result


def load_binary_function_data(proto_func, item_count: int) -> torch.Tensor:
    """
    Load binary function data into a PyTorch tensor.
    Returns a tensor of shape [1 + item_count, 1 + item_count]
    where tensor[i, j] = f(i, j) or 0 if undefined.
    """
    result = torch.zeros(1 + item_count, 1 + item_count, dtype=torch.int32)

    # Load data from the main message
    for row in proto_func.rows:
        lhs = row.lhs
        if lhs <= item_count and row.rhs_val.key:
            keys, vals = delta_decompress(row.rhs_val)
            for rhs, val in zip(keys, vals):
                if rhs <= item_count:
                    result[lhs, rhs] = val

    # Load data from blobs
    for hexdigest in proto_func.blobs:
        from pomagma.atlas.structure_pb2 import BinaryFunction

        chunks = load_blob_chunks(hexdigest, BinaryFunction)
        for chunk in chunks:
            for row in chunk.rows:
                lhs = row.lhs
                if lhs <= item_count and row.rhs_val.key:
                    keys, vals = delta_decompress(row.rhs_val)
                    for rhs, val in zip(keys, vals):
                        if rhs <= item_count:
                            result[lhs, rhs] = val

    return result


def load_symmetric_function_data(proto_func, item_count: int) -> torch.Tensor:
    """
    Load symmetric function data into a PyTorch tensor.
    For symmetric functions, we only store the lower triangle and mirror it.
    """
    result = torch.zeros(1 + item_count, 1 + item_count, dtype=torch.int32)

    # Load data from the main message
    for row in proto_func.rows:
        lhs = row.lhs
        if lhs <= item_count and row.rhs_val.key:
            keys, vals = delta_decompress(row.rhs_val)
            for rhs, val in zip(keys, vals):
                if rhs <= item_count:
                    result[lhs, rhs] = val
                    result[rhs, lhs] = val  # Mirror for symmetry

    # Load data from blobs
    for hexdigest in proto_func.blobs:
        from pomagma.atlas.structure_pb2 import BinaryFunction

        chunks = load_blob_chunks(hexdigest, BinaryFunction)
        for chunk in chunks:
            for row in chunk.rows:
                lhs = row.lhs
                if lhs <= item_count and row.rhs_val.key:
                    keys, vals = delta_decompress(row.rhs_val)
                    for rhs, val in zip(keys, vals):
                        if rhs <= item_count:
                            result[lhs, rhs] = val
                            result[rhs, lhs] = val  # Mirror for symmetry

    return result


def load_unary_relation_data(proto_rel, item_count: int) -> torch.Tensor:
    """
    Load unary relation data into a PyTorch tensor.
    Returns a boolean tensor of shape [1 + item_count].
    """
    result = torch.zeros(1 + item_count, dtype=torch.bool)

    # Load data from the main message
    if proto_rel.set.dense:
        dense_set = load_dense_set(proto_rel.set, item_count)
        result = dense_set

    # Load data from blobs
    for hexdigest in proto_rel.blobs:
        from pomagma.atlas.structure_pb2 import UnaryRelation

        chunks = load_blob_chunks(hexdigest, UnaryRelation)
        for chunk in chunks:
            if chunk.set.dense:
                dense_set = load_dense_set(chunk.set, item_count)
                result = result | dense_set  # Union

    return result


def load_binary_relation_data(proto_rel, item_count: int) -> torch.Tensor:
    """
    Load binary relation data into a PyTorch tensor.
    Returns a boolean tensor of shape [1 + item_count, 1 + item_count].
    """
    result = torch.zeros(1 + item_count, 1 + item_count, dtype=torch.bool)

    # Load data from the main message
    for row in proto_rel.rows:
        lhs = row.lhs
        if lhs <= item_count and row.rhs.dense:
            rhs_set = load_dense_set(row.rhs, item_count)
            result[lhs] = result[lhs] | rhs_set

    # Load data from blobs
    for hexdigest in proto_rel.blobs:
        from pomagma.atlas.structure_pb2 import BinaryRelation

        chunks = load_blob_chunks(hexdigest, BinaryRelation)
        for chunk in chunks:
            for row in chunk.rows:
                lhs = row.lhs
                if lhs <= item_count and row.rhs.dense:
                    rhs_set = load_dense_set(row.rhs, item_count)
                    result[lhs] = result[lhs] | rhs_set

    return result


@dataclass(frozen=True, slots=True, eq=False)
class Structure:
    """
    PyTorch representation of an algebraic structure. Immutable.
    """

    item_count: int
    nullary_functions: Mapping[str, int]
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
        return load_structure(filename, relations=relations)


def load_structure(filename: str, *, relations: bool = False) -> Structure:
    """
    Load a structure from a protobuf file.

    Args:
        filename: Path to the .pb file.
        relations: Whether to load relation data. Default: False.
    """
    # Load the main structure
    with InFile(blobstore.find_blob(blobstore.load_blob_ref(filename))) as f:
        proto_structure = ProtoStructure()
        f.read(proto_structure)

    item_count = proto_structure.carrier.item_count
    nullary_functions = {}
    injective_functions = {}
    binary_functions = {}
    symmetric_functions = {}
    unary_relations = {}
    binary_relations = {}

    # Load nullary functions
    constants = " ".join(
        sorted(proto_func.name for proto_func in proto_structure.nullary_functions)
    )
    logger.debug(f"Loading constants: {constants}")
    for proto_func in proto_structure.nullary_functions:
        nullary_functions[proto_func.name] = proto_func.val

    # Load injective functions
    for proto_func in proto_structure.injective_functions:
        logger.debug(f"Loading injective function: {proto_func.name}")
        tensor = load_injective_function_data(proto_func, item_count)
        injective_functions[proto_func.name] = tensor

    # Load binary functions
    for proto_func in proto_structure.binary_functions:
        logger.debug(f"Loading binary function: {proto_func.name}")
        tensor = load_binary_function_data(proto_func, item_count)
        binary_functions[proto_func.name] = tensor

    # Load symmetric functions
    for proto_func in proto_structure.symmetric_functions:
        logger.debug(f"Loading symmetric function: {proto_func.name}")
        tensor = load_symmetric_function_data(proto_func, item_count)
        symmetric_functions[proto_func.name] = tensor

    if relations:
        # Load unary relations
        for proto_rel in proto_structure.unary_relations:
            logger.debug(f"Loading unary relation: {proto_rel.name}")
            tensor = load_unary_relation_data(proto_rel, item_count)
            unary_relations[proto_rel.name] = tensor

        # Load binary relations
        for proto_rel in proto_structure.binary_relations:
            logger.debug(f"Loading binary relation: {proto_rel.name}")
            tensor = load_binary_relation_data(proto_rel, item_count)
            binary_relations[proto_rel.name] = tensor

    return Structure(
        item_count=item_count,
        nullary_functions=Map(nullary_functions),
        injective_functions=Map(injective_functions),
        binary_functions=Map(binary_functions),
        symmetric_functions=Map(symmetric_functions),
        unary_relations=Map(unary_relations),
        binary_relations=Map(binary_relations),
    )
