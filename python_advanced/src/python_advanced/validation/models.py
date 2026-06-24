"""Type hints, Pydantic models, and validation utilities."""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

T = TypeVar("T")


def first(iterable: list[T]) -> T | None:
    """
    Get the first element of a list using generic types.

    Args:
        iterable: List of items

    Returns:
        First item or None if list is empty
    """
    return iterable[0] if iterable else None


class PaymentMethod(Protocol):
    """Protocol for payment methods (structural subtyping)."""

    def process(self, amount: float) -> bool:
        """Process a payment."""
        ...

    def get_balance(self) -> float:
        """Get current balance."""
        ...


class CashPayment:
    """Cash payment implementation."""

    def __init__(self, initial_balance: float = 1000.0):
        """Initialize cash payment with balance."""
        self.balance = initial_balance

    def process(self, amount: float) -> bool:
        """Process cash payment."""
        if amount <= self.balance:
            self.balance -= amount
            return True
        return False

    def get_balance(self) -> float:
        """Get current cash balance."""
        return self.balance


class CoffeeOrder(BaseModel):
    """Pydantic model for a coffee order with validation."""

    order_id: int = Field(..., gt=0, description="Unique order identifier")
    customer_name: str = Field(..., min_length=1, max_length=100)
    coffee_type: Literal["espresso", "americano", "latte", "cappuccino", "macchiato"]
    size: Literal["small", "medium", "large"]
    quantity: int = Field(default=1, ge=1, le=100)
    price: float = Field(..., gt=0.0)
    status: Literal["pending", "preparing", "ready", "completed", "cancelled"] = "pending"
    special_instructions: str | None = Field(None, max_length=500)

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: str) -> str:
        """Validate and clean customer name."""
        return v.strip().title()

    @model_validator(mode="after")
    def validate_price_for_size(self) -> "CoffeeOrder":
        """Validate price matches size."""
        size_prices = {"small": (2.0, 3.0), "medium": (2.5, 3.5), "large": (3.0, 4.0)}
        min_price, max_price = size_prices.get(self.size, (2.0, 4.0))

        if not (min_price <= self.price <= max_price):
            msg = f"Price ${self.price} out of range for {self.size} coffee"
            raise ValueError(msg)
        return self


def process_cafe_order(
    order: CoffeeOrder, payment_method: PaymentMethod
) -> tuple[bool, str]:
    """
    Process a cafe order using a payment method.

    Args:
        order: Coffee order to process
        payment_method: Payment method (must implement PaymentMethod protocol)

    Returns:
        Tuple of (success, message)
    """
    if payment_method.process(order.price):
        return True, f"Order {order.order_id} processed successfully"
    return False, f"Insufficient funds for order {order.order_id}"
