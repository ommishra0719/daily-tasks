"""Performance module public API."""

from .optimization import (
    OptimizedTextChunk,
    PerformanceAnalyzer,
    calculate_overlap_score,
    calculate_overlap_score_optimized,
    heavy_cleaner,
    heavy_cleaner_optimized,
    run_pipeline,
    run_pipeline_optimized,
)

__all__ = [
    "OptimizedTextChunk",
    "PerformanceAnalyzer",
    "calculate_overlap_score",
    "calculate_overlap_score_optimized",
    "heavy_cleaner",
    "heavy_cleaner_optimized",
    "run_pipeline",
    "run_pipeline_optimized",
]
