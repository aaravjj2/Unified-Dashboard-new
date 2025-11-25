"""
Callback Registration Module
Registers all tab callbacks with the Dash app instance.

CRITICAL: This module is imported AFTER app.py completes initialization
to avoid circular import issues.
"""
import logging

logger = logging.getLogger(__name__)
from financial_dashboard.utils.callback_guards import install_guard, uninstall_guard

def register_all_callbacks(app, loaded_tabs, SH=None, CHATBOT_AVAILABLE=False, enabled_tabs=None):
    """
    Register all tab callbacks with the app.
    
    Args:
        app: The DashProxy app instance
        loaded_tabs: Dictionary of loaded tab modules
        SH: Shared helpers module (optional)
        CHATBOT_AVAILABLE: Whether chatbot UI is available
        enabled_tabs: List of tab IDs that are enabled (only these will have callbacks registered)
    """
    logger.info(f"[CALLBACK_REG] Starting callback registration. app object id: {id(app)}, type: {type(app)}")
    
    # Ensure we have a place to track which tabs have been registered
    if not hasattr(app, '_registered_tabs'):
        try:
            setattr(app, '_registered_tabs', set())
        except Exception:
            # Fallback: attach to server config
            app.server.config.setdefault('_registered_tabs', set())

    registered_count = 0
    
    for tab_id, tab_info in loaded_tabs.items():
        try:
            # CRITICAL FIX: Only register callbacks for enabled tabs to prevent duplicates
            if enabled_tabs is not None and tab_id not in enabled_tabs:
                logger.info(f"[CALLBACK_REG] Skipping disabled tab: {tab_id} ({tab_info.get('name')})")
                continue
                
            # Skip if this tab was already registered on this app instance
            registered_tabs = getattr(app, '_registered_tabs', None) or app.server.config.get('_registered_tabs')
            if registered_tabs and tab_id in registered_tabs:
                logger.info(f"[CALLBACK_REG] Skipping already-registered tab: {tab_id} ({tab_info.get('name')})")
                continue
            if hasattr(tab_info['module'], 'register_callbacks'):
                callback_func = tab_info['module'].register_callbacks
                logger.info(f"[CALLBACK_REG] Attempting to register callbacks for {tab_info['name']}")
                
                # ERROR BOUNDARY: Wrap callback registration in try/except to isolate tab failures
                try:
                    # Try different callback registration signatures
                    try:
                        # Register callbacks directly WITHOUT guard wrapper
                        # The guard wrapper was causing duplicate registrations
                        callback_func(app)
                        logger.info(f"✓ Registered callbacks for {tab_info['name']}")
                    except TypeError:
                        try:
                            callback_func(app, SH)
                            logger.info(f"✓ Registered callbacks for {tab_info['name']} (with SH)")
                        except Exception as e:
                            logger.error(f"Failed to register callbacks for {tab_info['name']}: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Continue to next tab - don't let one tab break others
                            continue
                except Exception as outer_e:
                    # Outer error boundary: catch ALL exceptions during callback registration
                    logger.error(f"⚠️ ERROR BOUNDARY: Tab '{tab_info['name']}' failed to register callbacks")
                    logger.error(f"Exception: {outer_e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # CRITICAL: Continue to next tab - isolate the failure
                    continue
                
                # NOTE: Do NOT call app.register_callbacks() here!
                # Calling it in the loop causes duplicate registrations.
                # It will be called ONCE after all tabs are processed.
                
                callback_count = len(getattr(app, 'callback_map', {}))
                logger.info(f"[CALLBACK_REG] Callback map now has {callback_count} entries after {tab_info['name']}")
                registered_count = callback_count
                # Mark this tab as registered to avoid duplicate registrations
                try:
                    if hasattr(app, '_registered_tabs'):
                        app._registered_tabs.add(tab_id)
                    else:
                        app.server.config.setdefault('_registered_tabs', set()).add(tab_id)
                except Exception:
                    logger.debug(f"[CALLBACK_REG] Could not mark tab as registered: {tab_id}")
                
        except Exception as e:
            logger.error(f"Error registering callbacks for {tab_info['name']}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Sprint 7: AI Chatbot Callbacks - RAG Integration
    if CHATBOT_AVAILABLE:
        try:
            from financial_dashboard.callbacks.chatbot_callbacks import register_chatbot_callbacks
            logger.info("🤖 Registering RAG-powered chatbot callbacks...")
            register_chatbot_callbacks(app)
            logger.info("✅ RAG chatbot callbacks registered successfully")
            registered_count += 1  # Count chatbot as one additional callback group
        except ImportError as e:
            logger.warning(f"⚠️ Chatbot callbacks module not found: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to register chatbot callbacks: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    final_callback_count = len(getattr(app, 'callback_map', {}))
    # CRITICAL FIX: Do NOT call app.register_callbacks() here!
    # DashProxy automatically registers callbacks when decorators are used
    # Calling register_callbacks() explicitly causes DUPLICATE REGISTRATIONS
    # This is the root cause of the button click failure bug
    logger.info(f"[CALLBACK_REG] Skipping app.register_callbacks() - DashProxy handles this automatically")
    logger.info(f"[CALLBACK_REG] Registration complete. Total callbacks: {final_callback_count}")
    
    return final_callback_count

