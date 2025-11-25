(function(){
    try {
        // If an element with this id already exists, don't override
        if (document.getElementById('chatbot-toggle-btn')) return;
        var btn = document.createElement('button');
        btn.id = 'chatbot-toggle-btn';
        btn.setAttribute('aria-label','chat toggle');
        btn.style.position='fixed';
        btn.style.bottom='30px';
        btn.style.right='30px';
        btn.style.width='64px';
        btn.style.height='64px';
        btn.style.borderRadius='50%';
        btn.style.zIndex='9998';
        btn.style.display='flex';
        btn.style.alignItems='center';
        btn.style.justifyContent='center';
        btn.style.background='linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        btn.style.border='none';
        btn.style.cursor='pointer';
        btn.style.boxShadow='0 4px 16px rgba(0,0,0,0.3)';
        btn.innerHTML = '<i class="fas fa-comments" style="font-size:28px;color:white"></i>';
        btn.addEventListener('click', function(){
            var container = document.getElementById('chatbot-container');
            if (!container) return;
            try {
                var cur = getComputedStyle(container).display;
                if (cur === 'none') {
                    container.style.display = 'block';
                    container.setAttribute('data-e2e-ready', 'true');
                } else {
                    container.style.display = 'none';
                    container.setAttribute('data-e2e-ready', 'false');
                }
            } catch (e) {
                // fallback
                container.style.display = (container.style.display === 'none') ? 'block' : 'none';
            }
        });
        document.addEventListener('DOMContentLoaded', function(){
            try { document.body.appendChild(btn); } catch(e){}
        });
    } catch(e) { console.error('e2e_chat_toggle error', e); }
})();
