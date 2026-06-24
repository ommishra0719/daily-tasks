"""Python Advanced: Capstone Package - Comprehensive Python Concepts.

Modules:
    core: Exceptions, settings, logging configuration
    validation: Type hints, Pydantic models, validation
    decorators: timeit, retry, UnstableAPI
    async_utils: Async HTTP operations, fetch, sequential_fetch, parallel_fetch
    pipeline: Generator-based document processing
    context: Context managers, descriptors, database connections
    strategy: Strategy pattern for document chunking
    performance: Performance optimization techniques and analysis

Example:
    >>> from python_advanced import CoffeeOrder, setup_logger, DocumentProcessor
    >>> logger = setup_logger()
    >>> order = CoffeeOrder(
    ...     order_id=1,
    ...     customer_name="Alice",
    ...     coffee_type="latte",
    ...     size="medium",
    ...     price=3.0,
    ... )
    >>> logger.info("Order created", extra={"order_id": order.order_id})
"""

__version__ = "1.0.0"
__author__ = "Quality Tech"

# Core exports
# Async exports
from python_advanced.async_utils import (
    fetch,
    parallel_fetch,
    sequential_fetch,
)

# Context exports
from python_advanced.context import (
    DatabaseConnection,
    Product,
    Validated,
    timer,
)
from python_advanced.core import (
    AppError,
    ConfigurationError,
    DatabaseConnectionError,
    FetchTimeoutError,
    HTTPRequestError,
    JSONDecodeError,
    ValidationError,
    settings,
    setup_logger,
)

# Decorators exports
from python_advanced.decorators import (
    UnstableAPI,
    retry,
    timeit,
)

# Performance exports
from python_advanced.performance import (
    OptimizedTextChunk,
    PerformanceAnalyzer,
    calculate_overlap_score,
    calculate_overlap_score_optimized,
    heavy_cleaner,
    heavy_cleaner_optimized,
    run_pipeline,
    run_pipeline_optimized,
)

# Pipeline exports
from python_advanced.pipeline import (
    chunk_lines,
    clean_lines,
    document_pipeline,
    process_file,
    read_lines,
)

# Strategy exports
from python_advanced.strategy import (
    ChunkerStrategy,
    DocumentProcessor,
    FixedSizeChunker,
    RecursiveChunker,
    SentenceChunker,
)

# Validation exports
from python_advanced.validation import (
    CashPayment,
    CoffeeOrder,
    PaymentMethod,
    first,
    process_cafe_order,
)

__all__ = [
    # Core
    "AppError",
    "CashPayment",
    # Strategy
    "ChunkerStrategy",
    "CoffeeOrder",
    "ConfigurationError",
    "DatabaseConnection",
    "DatabaseConnectionError",
    "DocumentProcessor",
    "FetchTimeoutError",
    "FixedSizeChunker",
    "HTTPRequestError",
    "JSONDecodeError",
    # Performance
    "OptimizedTextChunk",
    "PaymentMethod",
    "PerformanceAnalyzer",
    "Product",
    "RecursiveChunker",
    "SentenceChunker",
    "UnstableAPI",
    "Validated",
    "ValidationError",
    # Version and metadata
    "__version__",
    "calculate_overlap_score",
    "calculate_overlap_score_optimized",
    "chunk_lines",
    "clean_lines",
    "document_pipeline",
    # Async
    "fetch",
    # Validation
    "first",
    "heavy_cleaner",
    "heavy_cleaner_optimized",
    "parallel_fetch",
    "process_cafe_order",
    "process_file",
    # Pipeline
    "read_lines",
    "retry",
    "run_pipeline",
    "run_pipeline_optimized",
    "sequential_fetch",
    "settings",
    "setup_logger",
    # Decorators
    "timeit",
    # Context
    "timer",
]
