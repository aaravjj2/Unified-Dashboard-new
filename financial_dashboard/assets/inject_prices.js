(function(){
  function injectJSON(url, id){
    fetch(url, {cache: 'no-store'})
      .then(function(resp){ if(!resp.ok) throw new Error('fetch failed'); return resp.text(); })
      .then(function(text){
        try{
          var pre = document.getElementById(id);
          if(!pre){
            pre = document.createElement('pre');
            pre.id = id;
            pre.style.display = 'none';
            document.body.appendChild(pre);
          }
          pre.textContent = text;
        }catch(e){ console && console.warn && console.warn('inject_prices.js error', e); }
      })
      .catch(function(){ /* silent */ });
  }
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){
      injectJSON('/assets/prices_weekly.json', 'wp-prices-json');
      injectJSON('/assets/prices_monthly.json', 'mp-prices-json');
    });
  } else {
    injectJSON('/assets/prices_weekly.json', 'wp-prices-json');
    injectJSON('/assets/prices_monthly.json', 'mp-prices-json');
  }
})();
