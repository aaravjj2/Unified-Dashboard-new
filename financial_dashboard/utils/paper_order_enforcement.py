"""
Paper Trading Enforcement Utilities

Ensures all manual orders from Options Lab UI are paper-only unless
LIVE_ORDER_ALLOWED=true (default false).

Phase 31 Agent 1A - STEP 4
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
LIVE_ORDER_ALLOWED = os.getenv('LIVE_ORDER_ALLOWED', 'false').lower() == 'true'
AUDIT_LOG_PATH = 'reports/options_validation/diagnostics/order_audit.log'


def enforce_paper_order(order_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce paper-only trading constraint.
    
    Args:
        order_payload: Dict with order details
        
    Returns:
        Modified payload with paper=true enforced
        
    Raises:
        PermissionError: If live order attempted when LIVE_ORDER_ALLOWED=false
    """
    
    # Check if order explicitly requests live trading
    is_live_request = order_payload.get('paper', True) == False
    
    if is_live_request and not LIVE_ORDER_ALLOWED:
        # BLOCK: Live orders disabled
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': 'BLOCK_LIVE_ORDER',
            'order_payload': order_payload,
            'reason': 'LIVE_ORDER_ALLOWED=false',
            'blocked': True
        }
        
        _log_audit(audit_entry)
        
        raise PermissionError(
            "Live orders are disabled. Set LIVE_ORDER_ALLOWED=true to enable live trading. "
            "All orders are paper-only during validation."
        )
    
    # Force paper=true for safety
    order_payload['paper'] = True
    
    if is_live_request:
        # Log that we converted a live request to paper
        logger.warning(
            f"⚠️ Converted live order request to paper: "
            f"{order_payload.get('ticker')} {order_payload.get('action')}"
        )
    
    return order_payload


def validate_no_broker_calls():
    """
    Placeholder for network call validation.
    In production, would intercept all HTTP requests and block broker API calls.
    """
    # This would be implemented as a network interceptor/proxy
    # For now, we rely on paper flag enforcement at the order submission layer
    pass


def _log_audit(entry: Dict[str, Any]):
    """Append audit entry to log file"""
    Path(os.path.dirname(AUDIT_LOG_PATH)).mkdir(parents=True, exist_ok=True)
    
    with open(AUDIT_LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    
    logger.info(f"📝 Audit logged: {entry['action']}")


def save_paper_order(order: Dict[str, Any], storage_backend='json'):
    """
    Persist paper order to storage.
    
    Args:
        order: Order details dict
        storage_backend: 'json' or 'postgres'
    """
    
    if storage_backend == 'postgres':
        try:
            import psycopg2
            conn_string = os.getenv('DATABASE_URL')
            
            if not conn_string:
                logger.warning("DATABASE_URL not set, falling back to JSON")
                storage_backend = 'json'
            else:
                conn = psycopg2.connect(conn_string)
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO options_orders (
                        order_id, ticker, option_type, strike, expiration,
                        action, quantity, price, paper, status, created_at, user_id, notes, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    order.get('order_id'),
                    order.get('ticker'),
                    order.get('option_type'),
                    order.get('strike'),
                    order.get('expiration'),
                    order.get('action'),
                    order.get('quantity'),
                    order.get('price'),
                    order.get('paper', True),
                    order.get('status', 'pending'),
                    order.get('created_at', datetime.utcnow()),
                    order.get('user_id', 'test_user'),
                    order.get('notes'),
                    json.dumps(order.get('metadata', {}))
                ))
                
                conn.commit()
                cur.close()
                conn.close()
                
                logger.info(f"✅ Saved order {order['order_id']} to Postgres")
                return
                
        except Exception as e:
            logger.warning(f"Postgres save failed: {e}, falling back to JSON")
            storage_backend = 'json'
    
    # JSON fallback
    if storage_backend == 'json':
        json_file = 'financial_dashboard/data/options/orders.json'
        Path(os.path.dirname(json_file)).mkdir(parents=True, exist_ok=True)
        
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                orders = json.load(f)
        else:
            orders = []
        
        orders.append(order)
        
        with open(json_file, 'w') as f:
            json.dump(orders, f, indent=2)
        
        logger.info(f"✅ Saved order {order['order_id']} to JSON ({len(orders)} total)")
