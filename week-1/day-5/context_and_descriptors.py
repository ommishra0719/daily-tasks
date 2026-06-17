# context_and_descriptors.py

from contextlib import contextmanager, suppress
import pytest


# ==========================================================
# DATABASE CONNECTION CONTEXT MANAGER
# ==========================================================

class DatabaseConnection:
    """
    Mock database connection using a dictionary.
    Demonstrates __enter__, __exit__, and exception handling.
    """

    def __init__(self):
        self.connection = {}

    def __enter__(self):
        print("Connecting to database...")
        self.connection["connected"] = True
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"Exception occurred: {exc_val}")

        print("Disconnecting database...")
        self.connection["connected"] = False

        # False means exceptions are NOT suppressed
        return False


# ==========================================================
# GENERATOR-BASED CONTEXT MANAGER
# ==========================================================

@contextmanager
def timer():
    print("Timer started")

    try:
        yield

    finally:
        print("Timer stopped")


# ==========================================================
# VALIDATED DESCRIPTOR
# ==========================================================

class Validated:
    """
    Descriptor enforcing numeric min/max bounds.
    """

    def __init__(self, minimum=None, maximum=None):
        self.minimum = minimum
        self.maximum = maximum

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        if self.name not in obj.__dict__:
            raise AttributeError(f"{self.name} has not been set")

        return obj.__dict__[self.name]

    def __set__(self, obj, value):

        if not isinstance(value, (int, float)):
            raise TypeError(
                f"{self.name} must be numeric"
            )

        if self.minimum is not None and value < self.minimum:
            raise ValueError(
                f"{self.name} must be >= {self.minimum}"
            )

        if self.maximum is not None and value > self.maximum:
            raise ValueError(
                f"{self.name} must be <= {self.maximum}"
            )

        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        del obj.__dict__[self.name]


# ==========================================================
# CLASS USING DESCRIPTORS
# ==========================================================

class Product:
    price = Validated(0, 10000)
    quantity = Validated(1, 500)

    def __init__(self, price, quantity):
        self.price = price
        self.quantity = quantity


# ==========================================================
# PYTEST TESTS
# ==========================================================

def test_database_connection():
    with DatabaseConnection() as db:
        assert db["connected"] is True


def test_database_exception():
    with pytest.raises(ZeroDivisionError):
        with DatabaseConnection():
            1 / 0


def test_descriptor_valid_values():
    p = Product(100, 10)

    assert p.price == 100
    assert p.quantity == 10


def test_price_below_minimum():
    with pytest.raises(ValueError):
        Product(-5, 10)


def test_quantity_above_maximum():
    with pytest.raises(ValueError):
        Product(100, 1000)


def test_non_numeric_input():
    with pytest.raises(TypeError):
        Product("abc", 10)


def test_delete_attribute():
    p = Product(500, 20)

    del p.price

    with pytest.raises(AttributeError):
        _ = p.price


# ==========================================================
# OPTIONAL DEMO CODE
# ==========================================================

if __name__ == "__main__":

    print("\n--- Database Context Manager ---")

    with DatabaseConnection() as db:
        print("Inside with block")
        print(db)

    print("\n--- Generator Context Manager ---")

    with timer():
        print("Doing some work")

    print("\n--- Descriptor Demo ---")

    p = Product(250, 15)

    print("Price:", p.price)
    print("Quantity:", p.quantity)