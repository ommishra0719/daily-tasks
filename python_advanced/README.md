# Python Advanced: Capstone Package

A comprehensive Python package demonstrating advanced concepts including type hints, async programming, generators, decorators, design patterns, and performance optimization.

## Features

### Day 1: Type Hints & Validation
- **Generic types** with `TypeVar` for type-safe functions
- **Pydantic v2** models with field and model validators
- **Protocol** for structural subtyping
- **Type hints** throughout for better IDE support

### Day 2: Decorators & Testing
- `@timeit` decorator for execution time measurement
- `@retry` decorator factory with configurable attempts and delays
- `UnstableAPI` example with simulated failures
- Full pytest test coverage

### Day 3: Async & HTTP Operations
- Async HTTP fetching with `aiohttp`
- `asyncio.timeout` for timeout handling
- **Correlation IDs** (UUIDs) for request tracking
- Sequential and parallel fetch patterns
- Structured logging with correlation IDs

### Day 4: Generator Pipelines
- Memory-efficient file processing with generators
- Lazy evaluation for large documents
- Composable pipeline functions
- Statistics collection without loading entire files into memory

### Day 5: Context Managers & Descriptors
- `DatabaseConnection` context manager
- `Validated` descriptor with min/max bounds
- `@contextmanager` decorator for simple context managers
- Proper resource cleanup and exception handling

### Day 6: Strategy Design Pattern
- `ChunkerStrategy` abstract base class
- Multiple concrete implementations:
  - `FixedSizeChunker`: Fixed character count
  - `SentenceChunker`: Sentence-based splitting
  - `RecursiveChunker`: Hierarchical chunking
- `DocumentProcessor` for runtime strategy switching

### Day 8: Configuration & Logging
- **Pydantic Settings** for environment-based configuration
- **Loguru** for structured logging
- Dual output: stderr (colored) + JSON file
- Log rotation with compression
- Context binding for correlation IDs

### Day 9: Performance Optimization
- **Baseline vs Optimized implementations**
- LRU cache for expensive operations
- `__slots__` for memory efficiency
- Set operations for O(N+M) instead of O(N²)
- Performance analysis utilities

## Installation

### Development Installation

```bash
# Clone the repository
cd python_advanced

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
python -m pytest --cov=src/python_advanced

# Run type checking
mypy --strict src/python_advanced

# Run linting
ruff check src/python_advanced
```

### Production Installation

```bash
pip install python-advanced
```

## Usage

### Basic Type Hints & Validation

```python
from python_advanced import CoffeeOrder, process_cafe_order, CashPayment

# Create a validated order
order = CoffeeOrder(
    order_id=1,
    customer_name="alice",
    coffee_type="latte",
    size="medium",
    price=3.0,
    special_instructions="Extra hot"
)

# Process with payment
payment = CashPayment(100.0)
success, message = process_cafe_order(order, payment)
print(message)  # "Order 1 processed successfully"
```

### Decorators

```python
from python_advanced import timeit, retry, UnstableAPI

@timeit
@retry(max_attempts=3, delay=0.1)
def fetch_user_data(user_id: int):
    # Your code here
    pass

# Or use UnstableAPI directly
api = UnstableAPI(failure_rate=0.5)
result = api.fetch_data("/users")
```

### Async Operations

```python
import asyncio
from python_advanced import fetch, parallel_fetch

async def main():
    # Single fetch
    result = await fetch("https://api.example.com/data", request_id="req-123")
    
    # Multiple fetches in parallel
    urls = ["https://api.example.com/1", "https://api.example.com/2"]
    results = await parallel_fetch(urls)

asyncio.run(main())
```

### Pipeline Processing

```python
from python_advanced import document_pipeline, process_file

# Process large file efficiently with generators
for chunk in document_pipeline("large_file.txt", chunk_size=100):
    process_chunk(chunk)

# Get statistics
chunks, lines, chars = process_file("document.txt")
print(f"Processed {chunks} chunks with {lines} lines")
```

### Context Managers

```python
from python_advanced import DatabaseConnection, timer, Product, Validated

# Database connection
with DatabaseConnection("postgresql://localhost/mydb") as db:
    results = db.execute("SELECT * FROM users")

# Time a code block
with timer("data processing"):
    process_large_dataset()

# Use validated descriptor
product = Product("Laptop", price=999.99, quantity=10)
product.price = 1299.99  # Validated
product.price = -50.0  # Raises ValidationError
```

### Strategy Pattern

```python
from python_advanced import (
    DocumentProcessor,
    FixedSizeChunker,
    SentenceChunker,
    RecursiveChunker,
)

# Create processor with fixed-size strategy
processor = DocumentProcessor(FixedSizeChunker(chunk_size=100))
chunks = processor.process(document)

# Switch strategy at runtime
processor.set_strategy(SentenceChunker())
chunks = processor.process(document)

# Get strategy info
info = processor.get_strategy_info()
print(info)  # {'strategy': 'SentenceChunker', 'attributes': {}}
```

### Logging

```python
from python_advanced import setup_logger

logger = setup_logger()

# Simple logging
logger.info("Application started")

# Structured logging with correlation ID
logger.bind(request_id="abc-123").info("Processing request")

# The logs will be written to:
# - stderr (colored output for development)
# - logs/app.json (structured JSON for production)
```

### Performance Optimization

```python
from python_advanced import (
    run_pipeline,
    run_pipeline_optimized,
    PerformanceAnalyzer,
)

texts = ["text1", "text2", "text3"]

# Compare performance
results = PerformanceAnalyzer.compare_functions(
    run_pipeline,
    run_pipeline_optimized,
    texts,
    iterations=100
)

print(f"Speedup: {results['speedup']:.2f}x")
print(f"Improvement: {results['improvement_percent']:.2f}%")
```

## Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src/python_advanced --cov-report=html

# Run specific test file
python -m pytest tests/test_validation.py

# Run with verbose output
python -m pytest -v

# Run async tests
python -m pytest tests/test_async_utils.py -v

# Run slow tests only
python -m pytest -m slow
```

## Code Quality

### Type Checking (mypy with strict mode)

```bash
mypy --strict src/python_advanced
```

### Linting (ruff)

```bash
ruff check src/python_advanced
ruff check --fix src/python_advanced  # Auto-fix issues
```

### Code Formatting (black)

```bash
black src/python_advanced tests
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Project Structure

```
python_advanced/
├── pyproject.toml                 # Project metadata and dependencies
├── README.md                      # This file
├── .pre-commit-config.yaml        # Pre-commit hooks configuration
├── src/
│   └── python_advanced/
│       ├── __init__.py            # Package public API
│       ├── core/                  # Configuration, logging, exceptions
│       │   ├── __init__.py
│       │   ├── exceptions.py
│       │   ├── settings.py
│       │   └── logging_config.py
│       ├── validation/            # Type hints, Pydantic models
│       │   ├── __init__.py
│       │   └── models.py
│       ├── decorators/            # timeit, retry decorators
│       │   ├── __init__.py
│       │   ├── utils.py
│       │   └── api.py
│       ├── async_utils/           # Async HTTP operations
│       │   ├── __init__.py
│       │   └── fetch.py
│       ├── pipeline/              # Generator-based pipelines
│       │   ├── __init__.py
│       │   └── generators.py
│       ├── context/               # Context managers, descriptors
│       │   ├── __init__.py
│       │   └── managers.py
│       ├── strategy/              # Strategy design pattern
│       │   ├── __init__.py
│       │   └── chunker.py
│       └── performance/           # Optimization utilities
│           ├── __init__.py
│           └── optimization.py
└── tests/
    ├── __init__.py
    ├── conftest.py               # Pytest fixtures and configuration
    ├── test_core.py
    ├── test_validation.py
    ├── test_decorators.py
    ├── test_async_utils.py
    ├── test_pipeline.py
    ├── test_context.py
    ├── test_strategy.py
    └── test_performance.py
```

## SOLID Principles Applied

- **Single Responsibility**: Each class/function has one purpose
- **Open/Closed**: Use Strategy pattern for extensibility
- **Liskov Substitution**: All ChunkerStrategy implementations are interchangeable
- **Interface Segregation**: Protocol-based interfaces are minimal and focused
- **Dependency Inversion**: Depend on protocols, not concrete classes

## Performance Optimization Techniques

1. **Caching**: LRU cache for expensive operations
2. **Lazy Evaluation**: Generators for memory efficiency
3. **Algorithm Optimization**: Set operations (O(N+M)) vs nested loops (O(N²))
4. **Memory Efficiency**: `__slots__` to reduce object overhead
5. **Precomputation**: Calculate once, reuse multiple times

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Write tests for all new features
- Ensure type hints are complete (`mypy --strict`)
- Run pre-commit hooks before committing
- Keep docstrings comprehensive
- Follow SOLID principles

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Resources

- [PyPA Packaging Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Async Python (asyncio)](https://docs.python.org/3/library/asyncio.html)
- [Design Patterns in Python](https://refactoring.guru/design-patterns/python)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Loguru Documentation](https://loguru.readthedocs.io/)

## Author

Quality Tech - Advanced Python Training

## Version

1.0.0 - Initial release with all 9 days of concepts
