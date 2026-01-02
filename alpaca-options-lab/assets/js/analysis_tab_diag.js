(function(){
  try {
    const params = new URLSearchParams(window.location.search);
    if (!params.has('diag_tabs')) return;
    // Run after a short delay to let Dash render the tabs
    setTimeout(()=>{
      const ul = document.getElementById('analysis-hub-subtabs');
      if (!ul) { console.log('DIAG_TAB: no #analysis-hub-subtabs found'); return; }
      const anchors = ul.querySelectorAll('a.nav-link');
      console.log(`DIAG_TAB: found ${anchors.length} anchors`);
      anchors.forEach((a, idx)=>{
        console.log(`DIAG_TAB anchor[${idx}] textContent:'${a.textContent}' innerHTML:'${a.innerHTML}' children:${a.children.length}`);
        Array.from(a.childNodes).forEach((n, i)=>{
          console.log(`DIAG_TAB anchor[${idx}] node[${i}] type:${n.nodeType} name:${n.nodeName} value:'${n.nodeValue}'`);
        });
      });
      // Also log the tab panes labels
      const panes = document.querySelectorAll('.tab-pane');
      console.log(`DIAG_TAB: found ${panes.length} tab panes`);
      panes.forEach((p, i)=>{
        console.log(`DIAG_TAB pane[${i}] id:${p.id} hidden:${p.hidden} class:${p.className} innerText:'${p.innerText.slice(0,80)}'`);
      });
    }, 500);
  } catch(e){ console.log('DIAG_TAB: error', e); }
})();
