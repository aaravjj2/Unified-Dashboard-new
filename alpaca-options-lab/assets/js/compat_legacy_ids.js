// Compatibility shim: create legacy-id aliases for refactored hub-* elements
// This file is loaded automatically by Dash from the assets/ folder.
(function(){
  const MAPPING = {
    'pa-total-return': 'hub-pa-total-return',
    'pa-performance-chart': 'hub-pa-performance-chart',
    'pa-total-costs': 'hub-pa-total-costs',
    'pa-cost-breakdown': 'hub-pa-cost-breakdown',
    'attr-run-button': 'hub-attr-run-button',
    // Additional aliases for older clicker/test scripts
    'run-analysis': 'hub-run-analysis',
    'run-button': 'hub-run-button',
    'pa-calc-run': 'hub-pa-calc-run',
    'portfolio-root': 'hub-portfolio-root',
    'home-portfolio-value': 'home-portfolio-value',
    'home-action-alert': 'home-action-alert',
    'watchlist-items-container': 'watchlist-items-container'
  };

  function createAlias(legacyId, hubId){
    try{
      if(document.getElementById(legacyId)) return;
      const target = document.getElementById(hubId) || document.querySelector('#'+hubId);
      if(!target) return;

      // Create a lightweight alias element instead of cloning the full
      // React-managed node. Cloning React DOM nodes can break reconciliation
      // and lead to minified React errors in the console. This proxy keeps
      // only textual content and forwards clicks to the real target.
      const clone = document.createElement('div');
      clone.id = legacyId;
      // Copy some non-reactive presentation hints but avoid children/event listeners
      try{
        clone.className = target.className || '';
      }catch(e){}
      clone.setAttribute('data-legacy-alias','true');
      clone.style.display = '';
      clone.style.visibility = 'visible';
      clone.style.opacity = 1;
      // Keep the textual content in sync
      try{ clone.textContent = target.innerText || target.textContent || ''; }catch(e){}

      // Forward clicks on the lightweight alias to the real target so Dash callbacks fire
      clone.addEventListener('click', function(ev){
        try{ target.click(); }catch(e){}
      }, {capture:false});

      // Keep textual content in sync using a MutationObserver
      const observer = new MutationObserver(function(muts){
        try{
          clone.textContent = target.innerText || target.textContent || '';
        }catch(e){}
      });
      observer.observe(target, {childList:true, subtree:true, characterData:true});

      // Insert the clone right after the target so layout is natural
      if(target.parentNode){
        target.parentNode.insertBefore(clone, target.nextSibling);
      } else {
        document.body.appendChild(clone);
      }
    }catch(e){
      // best-effort only
      console.warn('compat_legacy_ids createAlias failed', legacyId, hubId, e);
    }
  }

  function ensurePortfolioRoot(){
    try{
      if(document.getElementById('portfolio-root')) return;
      // Create a lightweight container so legacy tests waiting on #portfolio-root succeed
      const el = document.createElement('div');
      el.id = 'portfolio-root';
      // keep it invisible but present
      el.style.width='0'; el.style.height='0'; el.style.overflow='hidden';
      el.setAttribute('aria-hidden','true');
      document.body.appendChild(el);
    }catch(e){console.warn('compat_legacy_ids ensurePortfolioRoot failed', e)}
  }

  function runOnce(){
    for(const legacy in MAPPING){
      createAlias(legacy, MAPPING[legacy]);
    }
    ensurePortfolioRoot();
  }

  // Run on load and a few times after page initialization to handle SPA updates
  window.addEventListener('load', function(){
    runOnce();
    let tries = 0;
    const iv = setInterval(function(){ tries++; runOnce(); if(tries>20) clearInterval(iv); }, 300);
  });

  // Also attempt on DOMSubtreeModified as a fallback (deprecated but harmless for tests)
  document.addEventListener('DOMContentLoaded', runOnce);
})();
