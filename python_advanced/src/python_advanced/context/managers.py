"""Context managers and descriptors for resource management and validation."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from loguru import logger

from ..core import DatabaseConnectionError, ValidationError


@contextmanager
def timer(name: str = "Operation") -> Generator[None, None, None]:
    """
    Context manager for timing code blocks.

    Args:
        name: Name of the operation being timed

    Yields:
        None

    Example:
        >>> with timer("Database query"):
        ...     execute_query()
    """
    import time

    logger.info(f"Starting: {name}")
    start = time.perf_counter()

    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"Completed {name} in {elapsed:.4f}s")


class DatabaseConnection:
    """Context manager for database connections."""

    def __init__(self, connection_string: str):
        """
        Initialize database connection context manager.

        Args:
            connection_string: Database connection string
        """
        self.connection_string = connection_string
        self.connected = False
        logger.debug(f"DatabaseConnection initialized with {connection_string}")

    def __enter__(self) -> "DatabaseConnection":
        """
        Establish database connection.

        Returns:
            Self

        Raises:
            DatabaseConnectionError: If connection fails
        """
        logger.info(f"Connecting to {self.connection_string}")
        try:
            # Simulated connection
            if "invalid" in self.connection_string:
                msg = f"Failed to connect to {self.connection_string}"
                raise ConnectionError(msg)
            self.connected = True
            logger.info("Connected successfully")
            return self
        except ConnectionError as e:
            raise DatabaseConnectionError(str(e)) from e

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """
        Close database connection.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value
            exc_tb: Exception traceback

        Returns:
            False (to propagate exceptions)
        """
        logger.info("Disconnecting from database")
        self.connected = False

        if exc_type is not None:
            logger.error(f"Exception occurred: {exc_type.__name__}: {exc_val}")
            return False  # Propagate exception

        return True

    def execute(self, query: str) -> list[str]:
        """
        Execute a database query.

        Args:
            query: SQL query to execute

        Returns:
            List of results (simulated)

        Raises:
            DatabaseConnectionError: If not connected
        """
        if not self.connected:
            msg = "Database is not connected"
            raise DatabaseConnectionError(msg)
        logger.debug(f"Executing query: {query}")
        return ["result1", "result2"]


class Validated:
    """Descriptor for validated numeric attributes with min/max bounds."""

    def __init__(self, name: str, min_value: float = 0.0, max_value: float = float("inf")):
        """
        Initialize validated descriptor.

        Args:
            name: Attribute name
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.private_name = f"_{name}"

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Set descriptor name (called automatically by Python).

        Args:
            owner: Class that owns the descriptor
            name: Attribute name on the class
        """
        self.private_name = f"_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        """
        Get validated attribute value.

        Args:
            obj: Instance
            objtype: Type of instance

        Returns:
            Attribute value

        Raises:
            AttributeError: If attribute not set
        """
        if obj is None:
            return self

        if not hasattr(obj, self.private_name):
            msg = f"{self.name} not set"
            raise AttributeError(msg)

        return getattr(obj, self.private_name)

    def __set__(self, obj: Any, value: Any) -> None:
        """
        Set validated attribute value.

        Args:
            obj: Instance
            value: New value

        Raises:
            ValidationError: If value is outside bounds
        """
        if not isinstance(value, (int, float)):
            msg = f"{self.name} must be numeric"
            raise ValidationError(msg)

        if not (self.min_value <= value <= self.max_value):
            msg = f"{self.name} must be between {self.min_value} and {self.max_value}"
            raise ValidationError(msg)

        setattr(obj, self.private_name, value)
        logger.debug(f"Set {self.name} = {value}")

    def __delete__(self, obj: Any) -> None:
        """
        Delete attribute.

        Args:
            obj: Instance
        """
        if hasattr(obj, self.private_name):
            delattr(obj, self.private_name)
            logger.debug(f"Deleted {self.name}")


class Product:
    """Example class using Validated descriptors."""

    price = Validated("price", min_value=0.01, max_value=100000.0)
    quantity = Validated("quantity", min_value=0, max_value=1000000)

    def __init__(self, name: str, price: float, quantity: int):
        """
        Initialize product.

        Args:
            name: Product name
            price: Product price
            quantity: Stock quantity
        """
        self.name = name
        self.price = price
        self.quantity = quantity

    def __repr__(self) -> str:
        """Get string representation."""
        return f"Product(name={self.name!r}, price={self.price}, quantity={self.quantity})"

    def total_value(self) -> float:
        """Calculate total inventory value."""
        price: float = self.price
        quantity: int = self.quantity
        return price * quantity
