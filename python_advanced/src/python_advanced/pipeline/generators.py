"""Generator-based pipelines for efficient document processing."""

from collections.abc import Generator
from itertools import islice
from pathlib import Path

from loguru import logger


def read_lines(filepath: Path | str) -> Generator[str, None, None]:
    """
    Read lines from a file lazily.

    Args:
        filepath: Path to the file

    Yields:
        Each line in the file

    Example:
        >>> for line in read_lines("large_file.txt"):
        ...     print(line)
    """
    filepath = Path(filepath)
    logger.debug(f"Reading lines from {filepath}")

    with open(filepath, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 10000 == 0:
                logger.debug(f"Read {line_num} lines from {filepath}")
            yield line


def clean_lines(lines: Generator[str, None, None]) -> Generator[str, None, None]:
    """
    Clean lines by stripping whitespace and filtering blank lines.

    Args:
        lines: Generator of lines

    Yields:
        Cleaned non-empty lines

    Example:
        >>> cleaned = clean_lines(read_lines("file.txt"))
    """
    for line in lines:
        cleaned = line.strip()
        if cleaned:  # Filter out empty lines
            yield cleaned


def chunk_lines(
    lines: Generator[str, None, None], chunk_size: int = 100
) -> Generator[list[str], None, None]:
    """
    Group lines into fixed-size chunks.

    Args:
        lines: Generator of lines
        chunk_size: Number of lines per chunk

    Yields:
        Lists of cleaned lines

    Example:
        >>> chunks = chunk_lines(clean_lines(read_lines("file.txt")), chunk_size=50)
        >>> for chunk in chunks:
        ...     process_chunk(chunk)
    """
    while True:
        chunk = list(islice(lines, chunk_size))
        if not chunk:
            break
        logger.debug(f"Yielding chunk of size {len(chunk)}")
        yield chunk


def document_pipeline(
    filepath: Path | str, chunk_size: int = 100
) -> Generator[list[str], None, None]:
    """
    Complete pipeline: read → clean → chunk.

    Args:
        filepath: Path to the document
        chunk_size: Lines per chunk

    Yields:
        Chunks of cleaned lines

    Example:
        >>> for chunk in document_pipeline("document.txt", chunk_size=100):
        ...     process_chunk(chunk)
    """
    lines = read_lines(filepath)
    cleaned = clean_lines(lines)
    chunks = chunk_lines(cleaned, chunk_size)
    yield from chunks


def process_file(
    filepath: Path | str, chunk_size: int = 100
) -> tuple[int, int, int]:
    """
    Process entire file through pipeline and return statistics.

    Args:
        filepath: Path to the file
        chunk_size: Lines per chunk

    Returns:
        Tuple of (total_chunks, total_lines, total_chars)

    Example:
        >>> chunks, lines, chars = process_file("large.txt", chunk_size=100)
        >>> print(f"Processed {chunks} chunks with {lines} lines and {chars} chars")
    """
    filepath = Path(filepath)
    logger.info(f"Processing {filepath} with chunk_size={chunk_size}")

    total_chunks = 0
    total_lines = 0
    total_chars = 0

    for chunk in document_pipeline(filepath, chunk_size):
        total_chunks += 1
        for line in chunk:
            total_lines += 1
            total_chars += len(line)

    logger.info(
        f"Finished processing {filepath}: "
        f"{total_chunks} chunks, {total_lines} lines, {total_chars} chars"
    )
    return total_chunks, total_lines, total_chars
