// Lightweight pointer-events fix only (CSS handles the rest for better performance)
(function(){
  function ensurePointerEvents(){
    try{
      const container = document.querySelector('[data-testid="trends-results-table-container"]')
                        || document.getElementById('results-table')
                        || document.getElementById('results-table-client')
                        || document.getElementById('results-area');
      if(!container) return;
      
      // Only fix pointer-events on table elements (CSS handles styling)
      const tables = container.querySelectorAll('table, .cell-table');
      tables.forEach(table => {
        // Set pointer-events on table and direct children only, not every cell
        table.style.pointerEvents = 'auto';
        const directChildren = table.querySelectorAll(':scope > thead, :scope > tbody, :scope > tr');
        directChildren.forEach(el => el.style.pointerEvents = 'auto');
      });
    }catch(e){
      console.error('ensurePointerEvents error', e);
    }
  }
  
  // Apply once after page load
  if(document.readyState === 'complete' || document.readyState === 'interactive'){
    setTimeout(ensurePointerEvents, 300);
  } else {
    document.addEventListener('DOMContentLoaded', ()=>setTimeout(ensurePointerEvents, 300));
  }
  
  // REMOVED: Heavy MutationObserver that was causing lag
  // CSS now handles all styling, JS only ensures pointer-events
})();
