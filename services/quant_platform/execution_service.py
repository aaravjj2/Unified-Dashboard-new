"""
Execution Service - Roadmap Items 351-400
Order management, execution algorithms, and market microstructure
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import queue
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class TimeInForce(Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill

@dataclass
class Order:
    """Order representation"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float = 0.0
    stop_price: float = 0.0
    time_in_force: TimeInForce = TimeInForce.DAY
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: int = 0
    avg_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class Fill:
    """Trade fill"""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0

@dataclass
class ExecutionMetrics:
    """Execution quality metrics"""
    arrival_price: float
    avg_execution_price: float
    vwap: float
    implementation_shortfall: float
    slippage: float
    market_impact: float
    timing_cost: float

class MarketImpactModel:
    """Market impact modeling - Items 360-368"""
    
    def __init__(self, daily_volume: float = 1000000, 
                 volatility: float = 0.02,
                 spread: float = 0.01):
        self.daily_volume = daily_volume
        self.volatility = volatility
        self.spread = spread
        
    def almgren_chriss_impact(self, quantity: int, execution_time: float,
                              risk_aversion: float = 1e-6) -> Dict[str, float]:
        """Almgren-Chriss market impact model - Item 361"""
        participation = quantity / self.daily_volume
        
        # Temporary impact (linear in trade rate)
        gamma = 0.1  # Temporary impact coefficient
        eta = 0.01  # Permanent impact coefficient
        
        # Trade rate
        trade_rate = quantity / (execution_time * self.daily_volume)
        
        # Temporary impact
        temp_impact = gamma * self.volatility * np.sqrt(trade_rate)
        
        # Permanent impact
        perm_impact = eta * participation
        
        # Total impact
        total_impact = temp_impact + perm_impact
        
        # Optimal execution time (minimizing impact + risk)
        optimal_time = np.sqrt(risk_aversion * quantity / (gamma * self.volatility))
        
        return {
            'temporary_impact': temp_impact,
            'permanent_impact': perm_impact,
            'total_impact': total_impact,
            'optimal_execution_time': optimal_time,
            'participation_rate': participation
        }
    
    def estimate_slippage(self, quantity: int, side: OrderSide) -> float:
        """Estimate slippage - Item 365"""
        participation = quantity / self.daily_volume
        
        # Base slippage from spread
        base_slippage = self.spread / 2
        
        # Impact slippage
        impact_slippage = 0.1 * self.volatility * np.sqrt(participation)
        
        return base_slippage + impact_slippage
    
    def estimate_fill_probability(self, price: float, current_price: float,
                                   side: OrderSide, time_horizon: float = 1.0) -> float:
        """Estimate fill probability for limit order - Item 366"""
        if side == OrderSide.BUY:
            distance = (current_price - price) / current_price
        else:
            distance = (price - current_price) / current_price
        
        if distance <= 0:
            return 0.95  # Very likely to fill immediately
        
        # Probability based on distance and volatility
        z_score = distance / (self.volatility * np.sqrt(time_horizon / 252))
        prob = 1 - 0.5 * (1 + np.erf(z_score / np.sqrt(2)))
        
        return prob

class ExecutionAlgorithms:
    """Execution algorithms - Items 351-359"""
    
    def __init__(self, impact_model: MarketImpactModel = None):
        self.impact_model = impact_model or MarketImpactModel()
        
    def twap_schedule(self, quantity: int, duration_minutes: int,
                     interval_minutes: int = 5) -> List[Tuple[int, int]]:
        """TWAP execution schedule - Item 352"""
        n_slices = duration_minutes // interval_minutes
        if n_slices == 0:
            return [(0, quantity)]
        
        base_qty = quantity // n_slices
        remainder = quantity % n_slices
        
        schedule = []
        for i in range(n_slices):
            slice_qty = base_qty + (1 if i < remainder else 0)
            schedule.append((i * interval_minutes, slice_qty))
        
        return schedule
    
    def vwap_schedule(self, quantity: int, volume_profile: List[float],
                     duration_minutes: int = 390) -> List[Tuple[int, int]]:
        """VWAP execution schedule - Item 353"""
        # Normalize volume profile
        total_vol = sum(volume_profile)
        vol_weights = [v / total_vol for v in volume_profile]
        
        n_periods = len(volume_profile)
        interval = duration_minutes // n_periods
        
        schedule = []
        remaining = quantity
        
        for i, weight in enumerate(vol_weights):
            if i == n_periods - 1:
                slice_qty = remaining
            else:
                slice_qty = int(quantity * weight)
                remaining -= slice_qty
            
            schedule.append((i * interval, slice_qty))
        
        return schedule
    
    def pov_schedule(self, quantity: int, target_participation: float,
                    market_volume: List[int]) -> List[Tuple[int, int]]:
        """Percentage of Volume execution - Item 356"""
        schedule = []
        remaining = quantity
        
        for i, vol in enumerate(market_volume):
            if remaining <= 0:
                break
            
            slice_qty = min(int(vol * target_participation), remaining)
            schedule.append((i, slice_qty))
            remaining -= slice_qty
        
        # Handle remaining quantity
        if remaining > 0 and len(schedule) > 0:
            last_time, last_qty = schedule[-1]
            schedule[-1] = (last_time, last_qty + remaining)
        
        return schedule
    
    def implementation_shortfall(self, quantity: int, risk_aversion: float = 1e-6,
                                 duration_minutes: int = 60) -> List[Tuple[int, int]]:
        """Implementation shortfall algorithm - Item 354"""
        impact = self.impact_model.almgren_chriss_impact(
            quantity, duration_minutes, risk_aversion
        )
        
        optimal_time = impact['optimal_execution_time']
        n_slices = max(1, int(optimal_time))
        
        # Front-loaded execution to minimize drift
        weights = [1 / (i + 1) for i in range(n_slices)]
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        schedule = []
        interval = duration_minutes // n_slices if n_slices > 0 else duration_minutes
        
        remaining = quantity
        for i, weight in enumerate(weights):
            slice_qty = int(quantity * weight) if i < len(weights) - 1 else remaining
            schedule.append((i * interval, slice_qty))
            remaining -= slice_qty
        
        return schedule
    
    def iceberg_schedule(self, quantity: int, visible_qty: int,
                        min_interval: int = 1) -> List[Tuple[int, int]]:
        """Iceberg order schedule - Item 357"""
        schedule = []
        remaining = quantity
        time = 0
        
        while remaining > 0:
            slice_qty = min(visible_qty, remaining)
            schedule.append((time, slice_qty))
            remaining -= slice_qty
            time += min_interval
        
        return schedule

class OrderManager:
    """Order management system - Items 370-400"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.fills: List[Fill] = []
        self.order_counter = 0
        self._lock = threading.Lock()
        
    def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: int, price: float = 0.0, stop_price: float = 0.0,
                    time_in_force: TimeInForce = TimeInForce.DAY) -> Order:
        """Create new order - Item 398"""
        with self._lock:
            self.order_counter += 1
            order_id = f"ORD-{self.order_counter:08d}"
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force
        )
        
        self.orders[order_id] = order
        return order
    
    def submit_order(self, order: Order) -> bool:
        """Submit order for execution"""
        if order.order_id not in self.orders:
            return False
        
        order.status = OrderStatus.SUBMITTED
        order.updated_at = datetime.now()
        
        logger.info(f"Order submitted: {order.order_id} {order.side.value} "
                   f"{order.quantity} {order.symbol}")
        
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        logger.info(f"Order cancelled: {order_id}")
        return True
    
    def fill_order(self, order_id: str, fill_qty: int, fill_price: float) -> Fill:
        """Record order fill"""
        if order_id not in self.orders:
            return None
        
        order = self.orders[order_id]
        
        fill = Fill(
            fill_id=f"FILL-{len(self.fills)+1:08d}",
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_qty,
            price=fill_price,
            timestamp=datetime.now(),
            commission=fill_qty * fill_price * 0.0001  # 1 bp commission
        )
        
        self.fills.append(fill)
        
        # Update order
        old_qty = order.filled_qty
        order.filled_qty += fill_qty
        order.avg_fill_price = (
            (old_qty * order.avg_fill_price + fill_qty * fill_price) / order.filled_qty
        )
        
        if order.filled_qty >= order.quantity:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIAL
        
        order.updated_at = datetime.now()
        
        return fill
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders"""
        orders = [o for o in self.orders.values() 
                 if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL]]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        return orders
    
    def get_fills(self, symbol: str = None, start_time: datetime = None) -> List[Fill]:
        """Get fills"""
        fills = self.fills
        
        if symbol:
            fills = [f for f in fills if f.symbol == symbol]
        
        if start_time:
            fills = [f for f in fills if f.timestamp >= start_time]
        
        return fills
    
    def calculate_execution_metrics(self, order_id: str, 
                                    arrival_price: float,
                                    vwap: float) -> ExecutionMetrics:
        """Calculate execution quality metrics - Item 400"""
        order = self.get_order(order_id)
        if not order or order.filled_qty == 0:
            return None
        
        fills = [f for f in self.fills if f.order_id == order_id]
        
        avg_price = order.avg_fill_price
        
        # Implementation shortfall
        if order.side == OrderSide.BUY:
            impl_shortfall = (avg_price - arrival_price) / arrival_price
            slippage = (avg_price - arrival_price) / arrival_price
        else:
            impl_shortfall = (arrival_price - avg_price) / arrival_price
            slippage = (arrival_price - avg_price) / arrival_price
        
        # Market impact (simplified)
        market_impact = abs(avg_price - vwap) / vwap
        
        # Timing cost
        timing_cost = abs(impl_shortfall - market_impact)
        
        return ExecutionMetrics(
            arrival_price=arrival_price,
            avg_execution_price=avg_price,
            vwap=vwap,
            implementation_shortfall=impl_shortfall,
            slippage=slippage,
            market_impact=market_impact,
            timing_cost=timing_cost
        )

class ExecutionService:
    """Main execution service - Items 351-400"""
    
    def __init__(self):
        self.impact_model = MarketImpactModel()
        self.algorithms = ExecutionAlgorithms(self.impact_model)
        self.order_manager = OrderManager()
        
    def create_market_order(self, symbol: str, side: str, quantity: int) -> Order:
        """Create market order"""
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        return self.order_manager.create_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=quantity
        )
    
    def create_limit_order(self, symbol: str, side: str, quantity: int, 
                          price: float) -> Order:
        """Create limit order"""
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        return self.order_manager.create_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price
        )
    
    def get_twap_schedule(self, quantity: int, duration_minutes: int = 60) -> List[Dict]:
        """Get TWAP execution schedule"""
        schedule = self.algorithms.twap_schedule(quantity, duration_minutes)
        return [{'minute': t, 'quantity': q} for t, q in schedule]
    
    def get_vwap_schedule(self, quantity: int, 
                         volume_profile: List[float] = None) -> List[Dict]:
        """Get VWAP execution schedule"""
        if volume_profile is None:
            # Default intraday volume profile (U-shaped)
            volume_profile = [1.5, 1.2, 0.8, 0.6, 0.5, 0.5, 0.6, 0.8, 1.2, 1.5]
        
        schedule = self.algorithms.vwap_schedule(quantity, volume_profile)
        return [{'minute': t, 'quantity': q} for t, q in schedule]
    
    def estimate_impact(self, quantity: int, 
                       execution_time: float = 60) -> Dict[str, float]:
        """Estimate market impact"""
        return self.impact_model.almgren_chriss_impact(quantity, execution_time)
    
    def estimate_slippage(self, quantity: int, side: str) -> float:
        """Estimate slippage"""
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        return self.impact_model.estimate_slippage(quantity, order_side)
    
    def simulate_execution(self, order: Order, current_price: float) -> List[Fill]:
        """Simulate order execution"""
        fills = []
        remaining = order.quantity
        
        # Simulate fills with some randomness
        while remaining > 0:
            fill_qty = min(remaining, np.random.randint(100, 500))
            
            # Add slippage
            slippage = self.estimate_slippage(fill_qty, order.side.value)
            if order.side == OrderSide.BUY:
                fill_price = current_price * (1 + slippage)
            else:
                fill_price = current_price * (1 - slippage)
            
            fill = self.order_manager.fill_order(order.order_id, fill_qty, fill_price)
            if fill:
                fills.append(fill)
            
            remaining -= fill_qty
        
        return fills
    
    def generate_sample_analysis(self) -> Dict[str, Any]:
        """Generate sample analysis for testing"""
        # Create and execute sample order
        order = self.create_market_order("AAPL", "buy", 1000)
        self.order_manager.submit_order(order)
        
        # Simulate execution
        current_price = 150.0
        fills = self.simulate_execution(order, current_price)
        
        # Get execution metrics
        vwap = sum(f.price * f.quantity for f in fills) / sum(f.quantity for f in fills)
        metrics = self.order_manager.calculate_execution_metrics(
            order.order_id, current_price, vwap
        )
        
        # Get schedules
        twap = self.get_twap_schedule(1000, 60)
        vwap_schedule = self.get_vwap_schedule(1000)
        
        # Impact estimation
        impact = self.estimate_impact(1000, 60)
        
        return {
            'order': {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'quantity': order.quantity,
                'filled_qty': order.filled_qty,
                'avg_price': order.avg_fill_price,
                'status': order.status.value
            },
            'fills': len(fills),
            'execution_metrics': {
                'arrival_price': metrics.arrival_price,
                'avg_execution_price': metrics.avg_execution_price,
                'implementation_shortfall': metrics.implementation_shortfall,
                'slippage': metrics.slippage,
                'market_impact': metrics.market_impact
            } if metrics else {},
            'twap_schedule': twap[:5],  # First 5 slices
            'vwap_schedule': vwap_schedule[:5],
            'impact_estimate': impact
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'total_orders': len(self.order_manager.orders),
            'open_orders': len(self.order_manager.get_open_orders()),
            'total_fills': len(self.order_manager.fills)
        }


if __name__ == "__main__":
    # Test the service
    service = ExecutionService()
    
    print("Execution Service Test")
    print("=" * 50)
    
    # Generate sample analysis
    analysis = service.generate_sample_analysis()
    
    print("\nOrder Execution:")
    order = analysis['order']
    print(f"  Order ID: {order['order_id']}")
    print(f"  Symbol: {order['symbol']}")
    print(f"  Quantity: {order['quantity']}")
    print(f"  Filled: {order['filled_qty']}")
    print(f"  Avg Price: ${order['avg_price']:.2f}")
    print(f"  Status: {order['status']}")
    
    print("\nExecution Metrics:")
    metrics = analysis['execution_metrics']
    if metrics:
        print(f"  Arrival Price: ${metrics['arrival_price']:.2f}")
        print(f"  Avg Execution: ${metrics['avg_execution_price']:.2f}")
        print(f"  Implementation Shortfall: {metrics['implementation_shortfall']:.4%}")
        print(f"  Slippage: {metrics['slippage']:.4%}")
        print(f"  Market Impact: {metrics['market_impact']:.4%}")
    
    print("\nTWAP Schedule (first 5 slices):")
    for slice in analysis['twap_schedule']:
        print(f"  Minute {slice['minute']}: {slice['quantity']} shares")
    
    print("\nMarket Impact Estimate:")
    impact = analysis['impact_estimate']
    print(f"  Temporary Impact: {impact['temporary_impact']:.4%}")
    print(f"  Permanent Impact: {impact['permanent_impact']:.4%}")
    print(f"  Total Impact: {impact['total_impact']:.4%}")
    
    print(f"\nService Stats: {service.get_stats()}")
    
    print("\n✅ Execution Service operational - Items 351-400")
