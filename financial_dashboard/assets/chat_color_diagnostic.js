/**
 * Chat Color Diagnostic Helper
 * Exposes computed chat color via window variable for Playwright tests
 * Part of RAG Chat Assistant Validation (PHASE 0)
 */

(function() {
    'use strict';
    
    // Initialize color diagnostic on DOM ready
    function initColorDiagnostic() {
        try {
            // Find chat container or response element
            const chatContainer = document.getElementById('chatbot-messages-container') 
                || document.querySelector('.chat-container')
                || document.querySelector('[id^="chat-response-"]');
            
            if (chatContainer) {
                const computedStyle = window.getComputedStyle(chatContainer);
                window.__chat_last_computed_color = computedStyle.color;
                
                // Also expose on a test-visible diagnostic element
                const diagnostic = document.getElementById('chat-color-diagnostic');
                if (diagnostic && diagnostic.dataset) {
                    diagnostic.dataset.computedColor = computedStyle.color;
                }
            }
        } catch (e) {
            console.warn('[ChatColorDiag] Error reading computed color:', e);
        }
    }
    
    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initColorDiagnostic);
    } else {
        initColorDiagnostic();
    }
    
    // Re-run whenever new chat messages appear (MutationObserver on chat container)
    const observeChatUpdates = () => {
        const chatMessages = document.getElementById('chatbot-messages');
        if (chatMessages) {
            const observer = new MutationObserver(() => {
                initColorDiagnostic();
            });
            observer.observe(chatMessages, { childList: true, subtree: true });
        }
    };
    
    // Delay observation setup slightly to ensure DOM is ready
    setTimeout(observeChatUpdates, 500);
    
})();
