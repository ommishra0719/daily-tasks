"""Tests for context managers and descriptors."""

import pytest

from python_advanced.context import DatabaseConnection, Product, timer
from python_advanced.core import DatabaseConnectionError, ValidationError


class TestTimer:
    """Test timer context manager."""

    def test_timer_context_manager(self) -> None:
        """Test that timer context manager works."""
        import time

        with timer("test operation"):
            time.sleep(0.01)
        # If we get here without exception, test passes


class TestDatabaseConnection:
    """Test DatabaseConnection context manager."""

    def test_database_connection_success(self) -> None:
        """Test successful database connection."""
        with DatabaseConnection("valid_connection_string") as db:
            assert db.connected is True

    def test_database_connection_auto_close(self) -> None:
        """Test that connection closes after context."""
        with DatabaseConnection("valid_connection_string") as db:
            assert db.connected is True
        assert db.connected is False

    def test_database_connection_invalid(self) -> None:
        """Test invalid database connection."""
        with pytest.raises(DatabaseConnectionError):
            DatabaseConnection("invalid_connection").__enter__()

    def test_database_execute_connected(self) -> None:
        """Test executing query on connected database."""
        with DatabaseConnection("valid_connection") as db:
            result = db.execute("SELECT * FROM users")
            assert len(result) == 2

    def test_database_execute_disconnected(self) -> None:
        """Test executing query on disconnected database."""
        db = DatabaseConnection("valid_connection")
        with pytest.raises(DatabaseConnectionError):
            db.execute("SELECT * FROM users")


class TestValidatedDescriptor:
    """Test Validated descriptor."""

    def test_validated_descriptor_set_get(self) -> None:
        """Test setting and getting validated value."""
        product = Product("Widget", price=10.0, quantity=5)
        assert product.price == 10.0
        assert product.quantity == 5

    def test_validated_descriptor_bounds(self) -> None:
        """Test descriptor enforces bounds."""
        product = Product("Widget", price=10.0, quantity=5)

        # Price out of bounds (too high)
        with pytest.raises(ValidationError):
            product.price = 150000.0

        # Price out of bounds (too low)
        with pytest.raises(ValidationError):
            product.price = 0.0

    def test_validated_descriptor_quantity_bounds(self) -> None:
        """Test quantity bounds validation."""
        product = Product("Widget", price=10.0, quantity=5)

        # Quantity out of bounds (too high)
        with pytest.raises(ValidationError):
            product.quantity = 2000000

        # Quantity out of bounds (negative)
        with pytest.raises(ValidationError):
            product.quantity = -1

    def test_validated_descriptor_invalid_type(self) -> None:
        """Test descriptor rejects non-numeric values."""
        product = Product("Widget", price=10.0, quantity=5)

        with pytest.raises(ValidationError):
            product.price = "not a number"  # type: ignore

    def test_validated_descriptor_delete(self) -> None:
        """Test deleting descriptor value."""
        product = Product("Widget", price=10.0, quantity=5)
        del product.price
        # After deletion, accessing should raise AttributeError
        with pytest.raises(AttributeError):
            _ = product.price


class TestProduct:
    """Test Product class using descriptors."""

    def test_product_creation(self) -> None:
        """Test creating a product."""
        product = Product("Widget", price=29.99, quantity=100)
        assert product.name == "Widget"
        assert product.price == 29.99
        assert product.quantity == 100

    def test_product_total_value(self) -> None:
        """Test calculating total inventory value."""
        product = Product("Widget", price=10.0, quantity=5)
        assert product.total_value() == 50.0

    def test_product_repr(self) -> None:
        """Test product string representation."""
        product = Product("Widget", price=10.0, quantity=5)
        repr_str = repr(product)
        assert "Widget" in repr_str
        assert "10.0" in repr_str
