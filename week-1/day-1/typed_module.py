from typing import List, Dict, Optional, Union, Tuple, TypeVar, Protocol, Literal, Final
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError

# ---------------------------------------------------------
# 1. Constants & Final
# ---------------------------------------------------------
STORE_NAME: Final[str] = "Python Cafe"

# ---------------------------------------------------------
# 2. Generics & TypeVar (Finding the first item in a line/list)
# ---------------------------------------------------------
T = TypeVar('T')

def first(lst: List[T]) -> Optional[T]:
    #Returns the first item in any list (e.g., first customer in line).
    if not lst:
        return None
    return lst[0]

# ---------------------------------------------------------
# 3. Protocol vs ABC (Structural Subtyping for Payment)
# ---------------------------------------------------------
class PaymentMethod(Protocol):
    #Any class with a 'pay' method fits this protocol implicitly.
    def pay(self, amount: float) -> bool: ...

class CashPayment:
    #No explicit inheritance needed; satisfies Protocol by structure.
    def pay(self, amount: float) -> bool:
        print(f"Paid ${amount} using cash.")
        return True

# ---------------------------------------------------------
# 4. Pydantic v2 Model (The Coffee Order Data Layer)
# ---------------------------------------------------------
class CoffeeOrder(BaseModel):
    order_id: int = Field(..., description="Receipt number")
    drink: str = Field(default="Latte")
    size: Literal["small", "medium", "large"] = "medium"
    status: Literal["placed", "ready"] = "placed"
    
    addons: Optional[Dict[str, str]] = None 

    @field_validator('order_id')
    @classmethod
    def validate_order_id(cls, value: int) -> int:
        #Field validator: Orders must have a valid positive receipt number.
        if value <= 0:
            raise ValueError("Order ID must be a positive number.")
        return value

    @model_validator(mode='after')
    def check_espresso_size(self) -> 'CoffeeOrder':
        #Model validator: Cross-field check between drink type and size.
        if self.drink == "Espresso" and self.size == "large":
            raise ValueError("Espresso cannot be ordered as a large size.")
        return self

# ---------------------------------------------------------
# 5. Strictly Annotated Function (PEP 484 & Tuples)
# ---------------------------------------------------------
def process_cafe_order(payment: PaymentMethod, receipt_id: int, choice: str, cup_size: str) -> Tuple[bool, Union[CoffeeOrder, str]]:
    #Takes a structural payment type and returns either an Order or an error string.
    try:
        payment.pay(4.50)
        
        new_order = CoffeeOrder(order_id=receipt_id, drink=choice, size=cup_size) # type: ignore
        return True, new_order
    except ValidationError as e:
        return False, str(e)

# ---------------------------------------------------------
# 6. Verification & Execution (Wrapped in a typed function)
# ---------------------------------------------------------
def main() -> None:
    print(f"--- Welcome to {STORE_NAME} ---")
    
    # 1. Test TypeVar / Generics
    order_queue: List[str] = ["Alice", "Bob", "Charlie"]
    
    # By annotating 'next_customer', we explicitly tell mypy that T is 'str'
    next_customer: Optional[str] = first(order_queue)
    print(f"Next customer in line: {next_customer}")

    print("\n--- 2. Processing a Valid Order ---")
    cash_wallet = CashPayment()
    success, result = process_cafe_order(cash_wallet, receipt_id=101, choice="Latte", cup_size="medium")
    
    if success and isinstance(result, CoffeeOrder):
        print("Order Created successfully:", result.model_dump())
        print("Order JSON Schema Keys:", list(result.model_json_schema()["properties"].keys()))

    print("\n--- 3. Testing Runtime Validation Failures ---")
    
    try:
        CoffeeOrder(order_id=0, drink="Coffee")
    except ValidationError:
        print("Caught Expected Error: Field validation stopped an invalid order ID (0).")

    try:
        CoffeeOrder(order_id=102, drink="Espresso", size="large")
    except ValidationError:
        print("Caught Expected Error: Cross-field validation stopped a 'large Espresso'.")

if __name__ == "__main__":
    main()