from dataclasses import dataclass
from enum import Enum
import time
import uuid


class OrderStatus(Enum):
    SUCCESS = "SUCCESS"
    RISK_REJECTED = "RISK_REJECTED"
    REJECTED = "REJECTED"


@dataclass
class ExecutionResult:
    success: bool
    fill_price: float = 0.0
    order_id: str = ""
    status: OrderStatus = OrderStatus.SUCCESS
    message: str = ""


class _OrderRouter:
    def __init__(self):
        self._history = []
        self._active = []

    def submit_order(self, ticker: str, side: str, quantity: int, order_type: str = "market", is_paper: bool = True) -> ExecutionResult:
        # Simple risk rule: reject quantities over 100
        if quantity > 100:
            return ExecutionResult(success=False, fill_price=0.0, order_id="", status=OrderStatus.RISK_REJECTED, message="Position size exceeds maximum allowed")

        fill_price = 100.0  # deterministic fill price for UI
        order_id = str(uuid.uuid4())
        result = ExecutionResult(success=True, fill_price=fill_price, order_id=order_id, status=OrderStatus.SUCCESS, message="Filled")

        record = {
            "order_id": order_id,
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "fill_price": fill_price,
            "status": result.status.value,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._history.insert(0, record)
        self._active.insert(0, record)
        return result

    def get_order_history(self, limit: int = 50):
        return self._history[:limit]

    def get_active_orders(self):
        return self._active


_SINGLETON = None


def get_order_router():
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = _OrderRouter()
    return _SINGLETON
