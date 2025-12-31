"""
Application initialization - Registers callbacks and sets layout.
This module is called by index.py AFTER both app and index modules are loaded,
breaking the circular import cycle.
"""
import logging
import json

logger = logging.getLogger(__name__)

def setup_callbacks_and_layout(app, index_module):
    """
    Register all callbacks and set the layout for the Dash app.
    
    Args:
        app: The DashProxy application instance
        index_module: The index module containing loaded_tabs, SH, CHATBOT_AVAILABLE, create_layout
    """
    logger.info("🔵 Setting up callbacks and layout...")
    
    # Register ALL callbacks BEFORE setting layout
    logger.info("🔵 Registering callbacks...")

    # 1. Register tab-specific callbacks via callbacks.py
    from financial_dashboard import callbacks
    try:
        _callback_count = callbacks.register_all_callbacks(
            app,
            loaded_tabs=index_module.loaded_tabs,
            SH=index_module.SH,
            CHATBOT_AVAILABLE=index_module.CHATBOT_AVAILABLE,
            enabled_tabs=index_module.ENABLED_TABS
        )
        logger.info(f"✅ Registered {_callback_count} tab callbacks")
    except Exception as e:
        logger.error(f"❌ Failed to register tab callbacks: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # 2. Register global callbacks (search, theme, chatbot)
    from financial_dashboard.index_callbacks_temp import register_global_callbacks
    try:
        _global_count = register_global_callbacks(
            app,
            loaded_tabs=index_module.loaded_tabs,
            CHATBOT_AVAILABLE=index_module.CHATBOT_AVAILABLE
        )
        logger.info(f"✅ Registered {_global_count} global callbacks")
    except Exception as e:
        logger.error(f"❌ Failed to register global callbacks: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # ============================================================================
    # CRITICAL FIX: Force DashProxy to register all pending callbacks FIRST
    # DashProxy uses lazy registration - decorators like @app.callback() don't
    # immediately populate callback_map. We must call register_callbacks() BEFORE
    # setting app.layout, otherwise React will fail to render components that
    # reference callback outputs that don't exist yet.
    # ============================================================================
    logger.info("🔵 Forcing DashProxy to register pending callbacks...")
    try:
        _before_count = len(getattr(app, 'callback_map', {}))
        logger.info(f"📊 Callback map BEFORE registration: {_before_count} entries")
        
        # CRITICAL FIX: Do NOT call app.register_callbacks() here!
        # It's already called in callbacks.py at line 169
        # Calling it twice causes duplicate callbacks (every callback 2x in /_dash-dependencies)
        # This breaks ALL button functionality because React doesn't know which callback to execute
        logger.warning("⚠️ SKIPPING app.register_callbacks() - already called in callbacks.py")
        logger.info("✅ Callbacks already hydrated in register_all_callbacks()")
        
        # Keep the count for logging
        _after_count = _before_count
        
        # ========================================================================
        # CRITICAL FIX: Deduplicate callbacks in callback_map AND dependencies endpoint
        # DashProxy creates duplicate entries - remove them to prevent React errors
        # ========================================================================
        if hasattr(app, 'callback_map') and app.callback_map:
            original_count = len(app.callback_map)
            seen_outputs = {}
            duplicates_removed = []
            
            for callback_id in list(app.callback_map.keys()):
                # Extract output signature (before @ symbol if present)
                output_sig = callback_id.split('@')[0] if '@' in callback_id else callback_id
                
                if output_sig in seen_outputs:
                    # Duplicate found - remove it
                    del app.callback_map[callback_id]
                    duplicates_removed.append(callback_id[:80])
                else:
                    seen_outputs[output_sig] = callback_id
            
            final_count = len(app.callback_map)
            logger.info(f"🔧 Deduplicated callback_map: {original_count} → {final_count} callbacks ({len(duplicates_removed)} duplicates removed)")
        
        _after_count = len(getattr(app, 'callback_map', {}))
        
        if _after_count == 0:
            logger.error("❌ CRITICAL: callback_map still empty! Check if tabs use @app.callback() decorators.")
        elif _after_count > 0:
            logger.info(f"✅ Successfully registered {_after_count} callbacks")
            # Log sample callback IDs for verification
            sample_keys = list(app.callback_map.keys())[:5]
            logger.info(f"📋 Sample callback IDs: {sample_keys}")
    except Exception as e:
        logger.error(f"❌ Failed to register callbacks: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # CRITICAL FIX: Call create_layout() to get actual layout component
    # The function reference approach was causing empty tabs on client side
    import time
    layout_timestamp = time.time()
    app.layout = index_module.create_layout()
    logger.info(f"✅ [app_init.py @ {layout_timestamp}] Set app.layout to actual layout (eagerly loaded)")
    
    logger.info("✅ Callbacks and layout setup complete")

