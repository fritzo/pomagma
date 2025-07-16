"""
Line profiling postprocessing utilities.

TODO parse SEQUENCE instructions and compute cumulative counts
"""

import hashlib
import logging
import os
from collections import Counter

logger = logging.getLogger(__name__)


def compute_file_hexdigest(filename: str) -> str:
    """Compute hexdigest of file content using SHA1."""
    hasher = hashlib.sha1()
    with open(filename, "rb") as f:
        while True:
            data = f.read(8192)
            if data:
                hasher.update(data)
            else:
                break
    return hasher.hexdigest()


def load_lineprof_data(lineprof_filename: str) -> Counter[int]:
    """
    Load line profiling data from a .lineprof file.

    Returns:
        Dict mapping byte offset to execution count
    """
    offset_to_count: Counter[int] = Counter()
    with open(lineprof_filename) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            offset_str, count_str = line.split("\t")
            offset = int(offset_str)
            count = int(count_str)
            offset_to_count[offset] += count
    return offset_to_count


def load_offset_to_line(programs_filename: str) -> tuple[dict[int, int], int]:
    """
    Load a mapping from byte offset to line number from a .programs file.

    Returns:
        Dict mapping byte offset to line number
    """
    offset_to_line: dict[int, int] = {}
    offset = 0
    with open(programs_filename) as f:
        for lineno, line in enumerate(f):
            # strip comments
            line = line.split("#", 1)[0].strip()
            tokens = line.split()
            if not tokens:
                continue
            offset_to_line[offset] = lineno
            offset += len(tokens)
    return offset_to_line, offset


def map_offsets_to_lines(
    programs_filename: str, offset_to_count: Counter[int]
) -> dict[int, int]:
    """
    Map byte offsets to line numbers in a .programs file.

    Returns:
        Dict mapping line number to total execution count
    """
    line_to_count: Counter[int] = Counter()
    offset_to_line, total_tokens = load_offset_to_line(programs_filename)
    for offset, count in offset_to_count.items():
        if offset > 2**31:
            # Work around offset bug
            offset = total_tokens + offset - 2**32
        line = offset_to_line[offset]
        line_to_count[line] += count
    return line_to_count


def annotate_programs_file(
    programs_filename: str, line_to_count: dict[int, int], output_filename: str
) -> None:
    """Create an annotated .programs file with execution counts as comments."""
    # Load lines from programs file
    lines: list[str] = []
    comment_column = 0
    with open(programs_filename) as f:
        for line in f:
            line = line.strip()
            # Remove trailing comments
            stripped = line.split("#", 1)[0].strip()
            comment_column = max(comment_column, len(stripped))
            lines.append(stripped or line)

    # Annotate lines with counts
    total_count = sum(line_to_count.values())
    for lineno, line in enumerate(lines):
        count = line_to_count.get(lineno, 0)
        if not count:
            continue
        percent = 100.0 * count / total_count
        line = line.ljust(comment_column)
        line = f"{line}  # {count:,} samples ({percent:.1f}%)"
        lines[lineno] = line

    # Save output file
    with open(output_filename, "w") as f:
        for line in lines:
            f.write(line)
            f.write("\n")


def process_programs_file(programs_filename: str) -> str | None:
    """
    Process a .programs file with its line profiling data.

    Returns:
        Path to the created annotated file, or None if no profiling data found
    """
    # Find corresponding .lineprof file
    hexdigest = compute_file_hexdigest(programs_filename)
    dirname = os.path.dirname(programs_filename)
    lineprof_filename = os.path.join(dirname, f"{hexdigest}.lineprof")
    if not os.path.exists(lineprof_filename):
        logger.warning("Missing profiling file for %s", programs_filename)
        return None

    # Load profiling data
    offset_to_count = load_lineprof_data(lineprof_filename)
    if not offset_to_count:
        logger.warning("Missing profiling data for %s", programs_filename)
        return None

    # Map offsets to line numbers
    line_to_count = map_offsets_to_lines(programs_filename, offset_to_count)

    # Create annotated output file
    base_name = os.path.splitext(programs_filename)[0]
    output_filename = f"{base_name}.lineprof.programs"
    annotate_programs_file(programs_filename, line_to_count, output_filename)
    total_samples = sum(line_to_count.values())
    logger.info("Created %s with %d total samples", output_filename, total_samples)
    return output_filename
