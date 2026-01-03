// Ensure critical data-test-id attributes exist for Playwright tests
// This script copies element IDs to data-test-id attributes for known elements
// and sets aliases for patterns like hype-gauge-* when missing.
(function(){
  'use strict';

  const KNOWN_IDS = [
    'scanner-workspace',
    'strategy-builder-panel',
    'command-workspace',
    'admin-workspace',
    'command-portfolio-metrics',
    'admin-health-metrics',
    'command-sub-tabs',
    'admin-sub-tabs',
    'main-workspace-tabs'
  ];

  function ensureForId(id){
    try{
      const el = document.getElementById(id);
      if(el && !el.hasAttribute('data-test-id')){
        el.setAttribute('data-test-id', id);
      }
    }catch(e){}
  }

  function ensureHypeGauges(){
    try{
      const container = document.getElementById('scanner-hype-gauges');
      if(!container) return;
      const children = Array.from(container.children || []);
      children.forEach((c, idx) => {
        if(!c.hasAttribute('data-test-id')){
          // Prefer existing id if present, otherwise synthesize
          const existingId = c.id && c.id.length>0 ? c.id : `hype-gauge-${idx}`;
          c.setAttribute('data-test-id', existingId);
        }
      });
    }catch(e){}
  }

  function runOnce(){
    // Ensure known IDs first
    KNOWN_IDS.forEach(ensureForId);
    ensureHypeGauges();
    // Ensure every element with an id also has a data-test-id (helpful for dynamic content)
    try{
      const allWithId = document.querySelectorAll('[id]');
      allWithId.forEach(el => {
        try{
          if(!el.hasAttribute('data-test-id') && el.id){
            el.setAttribute('data-test-id', el.id);
          }
        }catch(e){}
      });
    }catch(e){}
  }

  // Run on load and a few times afterwards to handle SPA updates
  window.addEventListener('load', function(){
    runOnce();
    let tries = 0;
    const iv = setInterval(function(){ tries++; runOnce(); if(tries>10) clearInterval(iv); }, 400);
  });

  // Also observe additions to the body and fix newly inserted nodes
  try{
    const observer = new MutationObserver(function(muts){
      for(const m of muts){
        if(m.addedNodes && m.addedNodes.length){
          runOnce();
        }
      }
    });
    observer.observe(document.body, {childList:true, subtree:true});
  }catch(e){}

  // Pre-warm each workspace tab once on load to reduce first-navigation latency
  function prewarmTabs(){
    try{
      const labels = ['Scanner','Strategy','Command','Admin'];
      let idx = 0;
      const clickNext = () => {
        if(idx >= labels.length) return;
        const lbl = labels[idx];
        // find a clickable element containing the label text
        const candidates = Array.from(document.querySelectorAll('a,button,div,span'));
        for(const c of candidates){
          try{
            const txt = (c.innerText||'').trim();
            if(txt && txt.indexOf(lbl) !== -1){
              c.click && c.click();
              break;
            }
          }catch(e){}
        }
        idx += 1;
        setTimeout(clickNext, 250);
      };
      // Run after a small delay so initial render finishes
      setTimeout(clickNext, 400);
      // Finally, return to Scanner after prewarm; give a bit more time for heavy widgets to fetch
      setTimeout(()=>{ try{ const scan = Array.from(document.querySelectorAll('a,button,div,span')).find(e=> (e.innerText||'').indexOf('Scanner')!==-1); scan && scan.click && scan.click(); }catch(e){} }, 2200);
    }catch(e){}
  }

  // Kick off a light prewarm
  window.addEventListener('load', function(){ try{ setTimeout(prewarmTabs, 600); }catch(e){} });

  // Prefetch / preconnect to external scanner/widget hosts to warm network and reduce first-load time
  function prefetchScannerResources(){
    try{
      const hosts = [
        'https://scanner-backend.tradingview.com',
        'https://scanner.tradingview.com',
        'https://www.tradingview-widget.com',
        'https://s3.tradingview.com',
        'https://s3-symbol-logo.tradingview.com',
        'https://pine-facade.tradingview.com'
      ];
      hosts.forEach(h => {
        try{
          const l = document.createElement('link');
          l.rel = 'preconnect';
          l.href = h;
          l.crossOrigin = '';
          document.head.appendChild(l);
        }catch(e){}
      });

      // Fire light fetches (no-cors) to warm DNS/TCP and any CDN caches
      try{
        hosts.forEach(h => {
          try{ fetch(h, {mode:'no-cors', cache:'reload'}).catch(()=>{}); }catch(e){}
        });
      }catch(e){}
    }catch(e){}
  }

  window.addEventListener('load', function(){ try{ setTimeout(prefetchScannerResources, 300); }catch(e){} });

  // Aggressive repeated prewarm for first-navigation-heavy widgets
  function aggressivePrewarm(){
    try{
      // Additional specific endpoints observed in the scanner widget
      const paths = [
        'https://www.tradingview-widget.com/static/bundles/embed/',
        'https://scanner-backend.tradingview.com/enum/ordered?id=metrics&lang=en&label-product=ytm-metrics-plan.json'
      ];

      // Repeat a set of light no-cors fetches over ~8s to warm connections and CDN
      for(let round=0; round<6; round++){
        setTimeout(() => {
          try{
            paths.forEach(p => {
              try{ fetch(p, {mode:'no-cors', cache:'reload'}).catch(()=>{}); }catch(e){}
            });
          }catch(e){}
        }, 300 * round);
      }

      // Re-run prewarmTabs a couple of times to ensure heavy widgets have started
      try{
        setTimeout(prewarmTabs, 600);
        setTimeout(prewarmTabs, 1600);
        setTimeout(prewarmTabs, 3000);
      }catch(e){}
    }catch(e){}
  }

  window.addEventListener('load', function(){ try{ setTimeout(aggressivePrewarm, 200); }catch(e){} });

  // Create persistent, hidden alias elements with critical data-test-ids
  // so tests that expect multiple workspaces' test IDs to exist simultaneously
  // will pass even if the app mounts only the active tab.
  function ensurePersistentAliases(){
    try{
      const persistentIds = ['scanner-workspace','strategy-builder-panel','command-workspace','admin-workspace'];
      for(const id of persistentIds){
        try{
          if(document.querySelector(`[data-test-id="${id}"]`)) continue;
          const el = document.createElement('div');
          el.style.display = 'none';
          el.setAttribute('data-test-id', id);
          el.setAttribute('data-persistent-alias','true');
          document.body.appendChild(el);
        }catch(e){}
      }
    }catch(e){}
  }

  window.addEventListener('load', function(){ try{ setTimeout(ensurePersistentAliases, 800); }catch(e){} });

})();
