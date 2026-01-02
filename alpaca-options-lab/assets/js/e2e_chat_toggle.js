/**
 * E2E Chat Toggle Helper
 * This script is DISABLED - the Dash layout creates the real chatbot-toggle-btn.
 * This was causing duplicate button IDs and breaking Playwright strict mode.
 * 
 * The real button is created in components/chatbot_ui.py -> create_floating_action_button()
 */
(function(){
    // DISABLED: No longer creating fallback button - Dash layout handles this
    // See: create_floating_action_button() in chatbot_ui.py
    console.log('[e2e_chat_toggle] DISABLED - Dash layout creates FAB button');
})();
