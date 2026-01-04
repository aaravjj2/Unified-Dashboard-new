"""
Alpaca Options Lab - Lifecycle Module

Option lifecycle management with:
- Position state machine (FSM)
- Assignment risk monitoring
- Rolling automation engine

Components:
- PositionFSM: State machine for position lifecycle
- AssignmentMonitor: Early assignment risk detection
- RollingEngine: Automated roll strategy execution
"""
from src.lifecycle.fsm import (
    PositionState,
    PositionEvent,
    Position,
    PositionFSM,
    get_position_manager,
)
from src.lifecycle.assignment import (
    AssignmentRisk,
    AssignmentMonitor,
    get_assignment_monitor,
)
from src.lifecycle.rolling import (
    RollStrategy,
    RollOpportunity,
    RollingEngine,
    get_rolling_engine,
)

__all__ = [
    "PositionState",
    "PositionEvent",
    "Position",
    "PositionFSM",
    "get_position_manager",
    "AssignmentRisk",
    "AssignmentMonitor",
    "get_assignment_monitor",
    "RollStrategy",
    "RollOpportunity",
    "RollingEngine",
    "get_rolling_engine",
]
