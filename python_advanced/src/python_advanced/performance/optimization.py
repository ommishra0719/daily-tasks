"""Performance optimization utilities and techniques."""

import functools
import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OptimizedTextChunk:
    """Text chunk with __slots__ for memory efficiency."""

    chunk_id: int
    text: str
    source: str
    metrics: dict[str, Any]


def heavy_cleaner(text: str) -> str:
    """
    Normalize text with regex operations (unoptimized baseline).

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    # Multiple passes - inefficient
    text = re.sub(r"\s+", " ", text)  # Multiple spaces to single
    text = re.sub(r"[^\w\s]", "", text)  # Remove special chars
    text = text.lower()
    return text.strip()


@functools.lru_cache(maxsize=512)
def heavy_cleaner_optimized(text: str) -> str:
    """
    Optimize heavy_cleaner with caching.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    # Single combined regex - more efficient
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = text.lower()
    return text.strip()


def calculate_overlap_score(text1: str, text2: str) -> float:
    """
    Calculate token overlap between two texts (unoptimized O(N*M)).

    Args:
        text1: First text
        text2: Second text

    Returns:
        Overlap score (0.0-1.0)
    """
    tokens1 = text1.split()
    tokens2 = text2.split()

    # Nested loop - O(N*M) complexity
    overlap = 0
    for token in tokens1:
        for token2 in tokens2:
            if token == token2:
                overlap += 1

    max_tokens = max(len(tokens1), len(tokens2))
    return overlap / max_tokens if max_tokens > 0 else 0.0


def calculate_overlap_score_optimized(text1: str, text2: str) -> float:
    """
    Optimize overlap score with set intersection O(N+M).

    Args:
        text1: First text
        text2: Second text

    Returns:
        Overlap score (0.0-1.0)
    """
    tokens1 = set(text1.split())
    tokens2 = set(text2.split())

    # Set intersection - O(N+M) complexity
    overlap = len(tokens1 & tokens2)
    max_tokens = max(len(tokens1), len(tokens2))
    return overlap / max_tokens if max_tokens > 0 else 0.0


def run_pipeline(texts: list[str]) -> list[OptimizedTextChunk]:
    """
    Process texts through pipeline (unoptimized with repeated operations).

    Args:
        texts: List of texts to process

    Returns:
        List of processed chunks
    """
    chunks: list[OptimizedTextChunk] = []

    for i, text in enumerate(texts):
        # Inefficient: cleaning done repeatedly for each comparison
        cleaned = heavy_cleaner(text)

        metrics: dict[str, Any] = {
            "token_count": len(cleaned.split()),
            "char_count": len(cleaned),
        }

        # Inefficient: O(N²) comparisons with repeated cleaning
        if i > 0:
            prev_cleaned = heavy_cleaner(texts[i - 1])  # Recalculated!
            metrics["overlap_with_prev"] = calculate_overlap_score(cleaned, prev_cleaned)

        chunk = OptimizedTextChunk(
            chunk_id=i, text=cleaned, source=f"text_{i}", metrics=metrics
        )
        chunks.append(chunk)

    return chunks


def run_pipeline_optimized(texts: list[str]) -> list[OptimizedTextChunk]:
    """
    Optimize pipeline with memoization and precomputation.

    Args:
        texts: List of texts to process

    Returns:
        List of processed chunks
    """
    chunks: list[OptimizedTextChunk] = []
    previous_cleaned: str | None = None

    for i, text in enumerate(texts):
        # Optimized: cleaning with LRU cache
        cleaned = heavy_cleaner_optimized(text)

        metrics: dict[str, Any] = {
            "token_count": len(cleaned.split()),
            "char_count": len(cleaned),
        }

        # Optimized: use cached previous value, O(N+M) overlap
        if previous_cleaned is not None:
            metrics["overlap_with_prev"] = calculate_overlap_score_optimized(
                cleaned, previous_cleaned
            )

        chunk = OptimizedTextChunk(
            chunk_id=i, text=cleaned, source=f"text_{i}", metrics=metrics
        )
        chunks.append(chunk)
        previous_cleaned = cleaned

    return chunks


class PerformanceAnalyzer:
    """Utility for analyzing and comparing performance optimizations."""

    @staticmethod
    def compare_functions(
        func_baseline: Any, func_optimized: Any, *args: Any, iterations: int = 100
    ) -> dict[str, Any]:
        """
        Compare execution time of baseline vs optimized function.

        Args:
            func_baseline: Original function
            func_optimized: Optimized function
            args: Arguments to pass to functions
            iterations: Number of iterations to time

        Returns:
            Dictionary with timing results
        """
        import time

        # Time baseline
        start = time.perf_counter()
        for _ in range(iterations):
            func_baseline(*args)
        baseline_time = time.perf_counter() - start

        # Time optimized
        start = time.perf_counter()
        for _ in range(iterations):
            func_optimized(*args)
        optimized_time = time.perf_counter() - start

        speedup = baseline_time / optimized_time if optimized_time > 0 else float("inf")

        return {
            "baseline_time": baseline_time,
            "optimized_time": optimized_time,
            "speedup": speedup,
            "improvement_percent": ((baseline_time - optimized_time) / baseline_time) * 100
            if baseline_time > 0
            else 0,
        }
