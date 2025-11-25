// Ensure Market Trends tab has stable id/data-testid for E2E tests
(function(){
  function setSentinel() {
    try {
      // Search for visible nav link or button containing 'Market Trends'
      const candidates = Array.from(document.querySelectorAll('a,button,.nav-link'));
      for (const el of candidates) {
        try {
          const txt = (el.innerText || el.textContent || '').trim();
          if (!txt) continue;
          if (txt.toLowerCase().includes('market trends')) {
            if (!el.id) el.id = 'tab-market_trends';
            el.setAttribute('data-testid', 'tab-market-trends');
            el.setAttribute('aria-label', 'Market Trends Tab');
            // mark on parent if direct link wrapped by list items
            if (el.parentElement && !el.parentElement.getAttribute('data-testid')) {
              el.parentElement.setAttribute('data-testid', 'tab-market-trends-wrapper');
            }
            console.info('[E2E SENTINEL] Market Trends sentinel applied', el);
            return true;
          }
        } catch(e){}
      }
    } catch(e){}
    return false;
  }

  // Try immediately and also observe DOM for late-inserted nav
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    if (setSentinel()) return;
  } else {
    document.addEventListener('DOMContentLoaded', function(){ setSentinel(); });
  }

  // MutationObserver to catch dynamic tab insertion
  const mo = new MutationObserver((mutations)=>{
    if (setSentinel()) {
      mo.disconnect();
    }
  });
  mo.observe(document.documentElement || document.body, {childList:true, subtree:true});

  // Safety: attempt again after a short delay in case scripts run later
  setTimeout(setSentinel, 3000);
  setTimeout(setSentinel, 8000);
})();
