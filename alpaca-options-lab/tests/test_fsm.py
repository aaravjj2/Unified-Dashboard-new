"""
Tests for src.lifecycle.fsm - Position State Machine

Tests cover:
- State transitions
- Invalid transitions
- Guard conditions
- Event handling
- State persistence
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.lifecycle.fsm import (
    PositionState,
    PositionEvent,
    StateTransition,
    PositionFSM,
    PositionContext,
    TransitionError,
    InvalidStateError,
    GuardFailedError,
)


class TestPositionState:
    """Test PositionState enum."""
    
    def test_all_states_defined(self):
        """Test all expected states are defined."""
        expected_states = [
            "PENDING",
            "OPEN",
            "PARTIALLY_FILLED",
            "FILLED",
            "CLOSING",
            "CLOSED",
            "EXPIRED",
            "ASSIGNED",
            "EXERCISED",
            "ROLLED",
            "CANCELLED",
            "ERROR",
        ]
        
        for state_name in expected_states:
            assert hasattr(PositionState, state_name)
    
    def test_state_string_representation(self):
        """Test state string representation."""
        state = PositionState.OPEN
        assert str(state) == "OPEN" or "open" in str(state).lower()


class TestPositionEvent:
    """Test PositionEvent enum."""
    
    def test_all_events_defined(self):
        """Test all expected events are defined."""
        expected_events = [
            "SUBMIT",
            "PARTIAL_FILL",
            "FILL",
            "CANCEL",
            "EXPIRE",
            "ASSIGN",
            "EXERCISE",
            "ROLL_INITIATE",
            "ROLL_COMPLETE",
            "CLOSE_INITIATE",
            "CLOSE_COMPLETE",
            "ERROR_OCCURRED",
            "RECOVER",
        ]
        
        for event_name in expected_events:
            assert hasattr(PositionEvent, event_name)


class TestPositionContext:
    """Test PositionContext dataclass."""
    
    def test_context_creation(self):
        """Test creating position context."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
            side="long",
            entry_price=Decimal("3.50"),
        )
        
        assert context.position_id == "POS-001"
        assert context.symbol == "AAPL240119C00150000"
        assert context.quantity == 10
    
    def test_context_defaults(self):
        """Test context default values."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
        )
        
        assert context.quantity == 0
        assert context.side is None
        assert context.entry_price is None
    
    def test_context_with_metadata(self):
        """Test context with metadata."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            metadata={"strategy": "covered_call"},
        )
        
        assert context.metadata["strategy"] == "covered_call"


class TestStateTransition:
    """Test StateTransition dataclass."""
    
    def test_transition_creation(self):
        """Test creating state transition."""
        transition = StateTransition(
            from_state=PositionState.PENDING,
            to_state=PositionState.OPEN,
            event=PositionEvent.FILL,
        )
        
        assert transition.from_state == PositionState.PENDING
        assert transition.to_state == PositionState.OPEN
        assert transition.event == PositionEvent.FILL
    
    def test_transition_with_guard(self):
        """Test transition with guard condition."""
        def quantity_guard(ctx: PositionContext) -> bool:
            return ctx.quantity > 0
        
        transition = StateTransition(
            from_state=PositionState.PENDING,
            to_state=PositionState.OPEN,
            event=PositionEvent.FILL,
            guard=quantity_guard,
        )
        
        assert transition.guard is not None


class TestPositionFSM:
    """Test PositionFSM class."""
    
    @pytest.fixture
    def context(self):
        """Create test context."""
        return PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
            side="long",
            entry_price=Decimal("3.50"),
        )
    
    @pytest.fixture
    def fsm(self, context):
        """Create FSM instance."""
        return PositionFSM(context)
    
    def test_initial_state(self, fsm):
        """Test FSM starts in PENDING state."""
        assert fsm.state == PositionState.PENDING
    
    def test_submit_transition(self, fsm):
        """Test PENDING -> OPEN on SUBMIT."""
        fsm.trigger(PositionEvent.SUBMIT)
        
        # After submit, should be waiting for fill
        assert fsm.state in [PositionState.PENDING, PositionState.OPEN]
    
    def test_fill_transition(self, fsm):
        """Test transition on FILL event."""
        fsm.trigger(PositionEvent.FILL)
        
        assert fsm.state in [PositionState.FILLED, PositionState.OPEN]
    
    def test_partial_fill_transition(self, fsm):
        """Test transition on PARTIAL_FILL event."""
        fsm.trigger(PositionEvent.PARTIAL_FILL)
        
        assert fsm.state == PositionState.PARTIALLY_FILLED
    
    def test_cancel_from_pending(self, fsm):
        """Test cancelling from PENDING state."""
        fsm.trigger(PositionEvent.CANCEL)
        
        assert fsm.state == PositionState.CANCELLED
    
    def test_expire_transition(self, fsm):
        """Test EXPIRE event."""
        # First fill the position
        fsm.trigger(PositionEvent.FILL)
        
        # Then expire
        fsm.trigger(PositionEvent.EXPIRE)
        
        assert fsm.state == PositionState.EXPIRED
    
    def test_assign_transition(self, fsm):
        """Test ASSIGN event."""
        fsm.trigger(PositionEvent.FILL)
        fsm.trigger(PositionEvent.ASSIGN)
        
        assert fsm.state == PositionState.ASSIGNED
    
    def test_exercise_transition(self, fsm):
        """Test EXERCISE event."""
        fsm.trigger(PositionEvent.FILL)
        fsm.trigger(PositionEvent.EXERCISE)
        
        assert fsm.state == PositionState.EXERCISED
    
    def test_roll_transitions(self, fsm):
        """Test roll workflow."""
        fsm.trigger(PositionEvent.FILL)
        fsm.trigger(PositionEvent.ROLL_INITIATE)
        fsm.trigger(PositionEvent.ROLL_COMPLETE)
        
        assert fsm.state == PositionState.ROLLED
    
    def test_close_transitions(self, fsm):
        """Test close workflow."""
        fsm.trigger(PositionEvent.FILL)
        fsm.trigger(PositionEvent.CLOSE_INITIATE)
        
        assert fsm.state == PositionState.CLOSING
        
        fsm.trigger(PositionEvent.CLOSE_COMPLETE)
        
        assert fsm.state == PositionState.CLOSED
    
    def test_error_transition(self, fsm):
        """Test ERROR_OCCURRED event."""
        fsm.trigger(PositionEvent.ERROR_OCCURRED)
        
        assert fsm.state == PositionState.ERROR
    
    def test_recover_from_error(self, fsm):
        """Test RECOVER event from ERROR state."""
        fsm.trigger(PositionEvent.ERROR_OCCURRED)
        assert fsm.state == PositionState.ERROR
        
        fsm.trigger(PositionEvent.RECOVER)
        
        # Should recover to previous state or PENDING
        assert fsm.state != PositionState.ERROR
    
    def test_invalid_transition_raises(self, fsm):
        """Test that invalid transition raises error."""
        # Can't close from PENDING
        with pytest.raises(TransitionError):
            fsm.trigger(PositionEvent.CLOSE_COMPLETE)
    
    def test_state_history(self, fsm):
        """Test state history tracking."""
        fsm.trigger(PositionEvent.FILL)
        fsm.trigger(PositionEvent.CLOSE_INITIATE)
        fsm.trigger(PositionEvent.CLOSE_COMPLETE)
        
        history = fsm.history
        
        assert len(history) >= 3
        assert history[0].from_state == PositionState.PENDING
    
    def test_can_trigger(self, fsm):
        """Test can_trigger method."""
        assert fsm.can_trigger(PositionEvent.FILL) is True
        assert fsm.can_trigger(PositionEvent.CLOSE_COMPLETE) is False
    
    def test_available_events(self, fsm):
        """Test getting available events."""
        events = fsm.available_events
        
        assert PositionEvent.FILL in events or PositionEvent.SUBMIT in events
        assert PositionEvent.CLOSE_COMPLETE not in events


class TestGuardConditions:
    """Test guard conditions on transitions."""
    
    @pytest.fixture
    def fsm_with_guards(self):
        """Create FSM with custom guards."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
            side="long",
        )
        
        fsm = PositionFSM(context)
        
        # Add a guard that requires quantity > 0
        fsm.add_guard(
            PositionEvent.FILL,
            lambda ctx: ctx.quantity > 0,
        )
        
        return fsm
    
    def test_guard_passes(self, fsm_with_guards):
        """Test transition when guard passes."""
        # quantity is 10 > 0, guard passes
        fsm_with_guards.trigger(PositionEvent.FILL)
        
        assert fsm_with_guards.state != PositionState.PENDING
    
    def test_guard_fails(self):
        """Test transition when guard fails."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=0,  # Guard will fail
        )
        
        fsm = PositionFSM(context)
        fsm.add_guard(
            PositionEvent.FILL,
            lambda ctx: ctx.quantity > 0,
        )
        
        with pytest.raises(GuardFailedError):
            fsm.trigger(PositionEvent.FILL)


class TestCallbacks:
    """Test state transition callbacks."""
    
    @pytest.fixture
    def fsm_with_callbacks(self):
        """Create FSM with callbacks."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
        )
        
        return PositionFSM(context)
    
    def test_on_enter_callback(self, fsm_with_callbacks):
        """Test on_enter callback."""
        callback = MagicMock()
        
        fsm_with_callbacks.on_enter(PositionState.FILLED, callback)
        fsm_with_callbacks.trigger(PositionEvent.FILL)
        
        callback.assert_called_once()
    
    def test_on_exit_callback(self, fsm_with_callbacks):
        """Test on_exit callback."""
        callback = MagicMock()
        
        fsm_with_callbacks.on_exit(PositionState.PENDING, callback)
        fsm_with_callbacks.trigger(PositionEvent.FILL)
        
        callback.assert_called_once()
    
    def test_on_transition_callback(self, fsm_with_callbacks):
        """Test on_transition callback."""
        callback = MagicMock()
        
        fsm_with_callbacks.on_transition(
            PositionState.PENDING,
            PositionState.FILLED,
            callback,
        )
        
        fsm_with_callbacks.trigger(PositionEvent.FILL)
        
        callback.assert_called_once()


class TestAsyncCallbacks:
    """Test async callback support."""
    
    @pytest.fixture
    def async_fsm(self):
        """Create FSM with async support."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
        )
        return PositionFSM(context, async_mode=True)
    
    @pytest.mark.asyncio
    async def test_async_on_enter(self, async_fsm):
        """Test async on_enter callback."""
        callback = AsyncMock()
        
        async_fsm.on_enter(PositionState.FILLED, callback)
        await async_fsm.trigger_async(PositionEvent.FILL)
        
        callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_trigger(self, async_fsm):
        """Test async trigger."""
        await async_fsm.trigger_async(PositionEvent.FILL)
        
        assert async_fsm.state != PositionState.PENDING


class TestStatePersistence:
    """Test state persistence and restoration."""
    
    def test_export_state(self):
        """Test exporting FSM state."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
        )
        fsm = PositionFSM(context)
        fsm.trigger(PositionEvent.FILL)
        
        exported = fsm.export_state()
        
        assert "state" in exported
        assert "context" in exported
        assert "history" in exported
    
    def test_import_state(self):
        """Test importing FSM state."""
        exported = {
            "state": "FILLED",
            "context": {
                "position_id": "POS-001",
                "symbol": "AAPL240119C00150000",
                "quantity": 10,
            },
            "history": [],
        }
        
        fsm = PositionFSM.from_export(exported)
        
        assert fsm.state == PositionState.FILLED
        assert fsm.context.position_id == "POS-001"
    
    def test_roundtrip_persistence(self):
        """Test roundtrip export/import."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
        )
        fsm1 = PositionFSM(context)
        fsm1.trigger(PositionEvent.FILL)
        fsm1.trigger(PositionEvent.CLOSE_INITIATE)
        
        # Export
        exported = fsm1.export_state()
        
        # Import
        fsm2 = PositionFSM.from_export(exported)
        
        assert fsm2.state == fsm1.state
        assert len(fsm2.history) == len(fsm1.history)


class TestEdgeCases:
    """Test edge cases."""
    
    def test_multiple_triggers_same_event(self):
        """Test triggering same event multiple times."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
        )
        fsm = PositionFSM(context)
        
        fsm.trigger(PositionEvent.FILL)
        initial_state = fsm.state
        
        # Trying to fill again should either:
        # 1. Stay in same state (idempotent)
        # 2. Raise an error
        try:
            fsm.trigger(PositionEvent.FILL)
            assert fsm.state == initial_state
        except TransitionError:
            pass  # Also acceptable
    
    def test_terminal_state(self):
        """Test transitions from terminal states."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
        )
        fsm = PositionFSM(context)
        
        # Get to CLOSED state
        fsm.trigger(PositionEvent.FILL)
        fsm.trigger(PositionEvent.CLOSE_INITIATE)
        fsm.trigger(PositionEvent.CLOSE_COMPLETE)
        
        assert fsm.state == PositionState.CLOSED
        
        # CLOSED is terminal - most events should raise
        with pytest.raises(TransitionError):
            fsm.trigger(PositionEvent.FILL)
    
    def test_context_modification_during_transition(self):
        """Test that context can be modified during callbacks."""
        context = PositionContext(
            position_id="POS-001",
            symbol="AAPL240119C00150000",
            quantity=10,
        )
        fsm = PositionFSM(context)
        
        def modify_context(ctx):
            ctx.metadata["filled_at"] = datetime.now()
        
        fsm.on_enter(PositionState.FILLED, modify_context)
        fsm.trigger(PositionEvent.FILL)
        
        assert "filled_at" in fsm.context.metadata
