"""Tests for validation module."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from python_advanced.validation import (
    CashPayment,
    CoffeeOrder,
    first,
    process_cafe_order,
)


class TestGenericFirst:
    """Test generic first() function."""

    def test_first_with_items(self) -> None:
        """Test first() with non-empty list."""
        assert first([1, 2, 3]) == 1
        assert first(["a", "b", "c"]) == "a"

    def test_first_with_empty_list(self) -> None:
        """Test first() with empty list."""
        assert first([]) is None

    def test_first_with_single_item(self) -> None:
        """Test first() with single item."""
        assert first([42]) == 42


class TestCashPayment:
    """Test CashPayment protocol implementation."""

    def test_cash_payment_initialization(self) -> None:
        """Test CashPayment initialization."""
        payment = CashPayment(1000.0)
        assert payment.get_balance() == 1000.0

    def test_cash_payment_process_success(self) -> None:
        """Test successful payment."""
        payment = CashPayment(100.0)
        assert payment.process(50.0) is True
        assert payment.get_balance() == 50.0

    def test_cash_payment_insufficient_funds(self) -> None:
        """Test payment with insufficient funds."""
        payment = CashPayment(50.0)
        assert payment.process(100.0) is False
        assert payment.get_balance() == 50.0  # Balance unchanged

    def test_cash_payment_exact_amount(self) -> None:
        """Test payment with exact amount."""
        payment = CashPayment(100.0)
        assert payment.process(100.0) is True
        assert payment.get_balance() == 0.0


class TestCoffeeOrder:
    """Test CoffeeOrder Pydantic model."""

    def test_valid_coffee_order(self) -> None:
        """Test creating valid coffee order."""
        order = CoffeeOrder(
            order_id=1,
            customer_name="alice",
            coffee_type="latte",
            size="medium",
            price=3.0,
        )
        assert order.order_id == 1
        assert order.customer_name == "Alice"  # Normalized
        assert order.status == "pending"

    def test_coffee_order_invalid_order_id(self) -> None:
        """Test coffee order with invalid order_id."""
        with pytest.raises(PydanticValidationError):
            CoffeeOrder(
                order_id=0,
                customer_name="alice",
                coffee_type="latte",
                size="medium",
                price=3.0,
            )

    def test_coffee_order_invalid_coffee_type(self) -> None:
        """Test coffee order with invalid coffee type."""
        with pytest.raises(PydanticValidationError):
            CoffeeOrder(
                order_id=1,
                customer_name="alice",
                coffee_type="invalid",  # type: ignore
                size="medium",
                price=3.0,
            )

    def test_coffee_order_price_bounds(self) -> None:
        """Test coffee order price validation."""
        # Price too low for medium
        with pytest.raises(ValueError):
            CoffeeOrder(
                order_id=1,
                customer_name="alice",
                coffee_type="latte",
                size="medium",
                price=1.0,
            )

        # Price too high for small
        with pytest.raises(ValueError):
            CoffeeOrder(
                order_id=1,
                customer_name="alice",
                coffee_type="latte",
                size="small",
                price=5.0,
            )

    def test_coffee_order_with_instructions(self) -> None:
        """Test coffee order with special instructions."""
        order = CoffeeOrder(
            order_id=1,
            customer_name="alice",
            coffee_type="latte",
            size="large",
            price=3.5,
            special_instructions="Extra hot, no foam",
        )
        assert order.special_instructions == "Extra hot, no foam"


class TestProcessCafeOrder:
    """Test process_cafe_order function."""

    def test_process_order_success(self) -> None:
        """Test successful order processing."""
        order = CoffeeOrder(
            order_id=1,
            customer_name="alice",
            coffee_type="latte",
            size="medium",
            price=3.0,
        )
        payment = CashPayment(100.0)

        success, message = process_cafe_order(order, payment)
        assert success is True
        assert "successfully" in message.lower()

    def test_process_order_insufficient_funds(self) -> None:
        """Test order processing with insufficient funds."""
        order = CoffeeOrder(
            order_id=1,
            customer_name="alice",
            coffee_type="latte",
            size="medium",
            price=3.0,
        )
        payment = CashPayment(1.0)

        success, message = process_cafe_order(order, payment)
        assert success is False
        assert "insufficient" in message.lower()
