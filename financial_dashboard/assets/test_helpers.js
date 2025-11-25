// Test helpers for Playwright / automated tests
// Expose a function to programmatically activate dashboard tabs by visible text.
window.selectDashboardTab = function(tabLabel) {
    try {
        const norm = (s) => (s || '').toString().trim().toLowerCase();
        // Search for obvious containers
        const containers = [document.querySelector('#dashboard-tabs'), document];
        for (const container of containers) {
            if (!container) continue;
            const candidates = container.querySelectorAll('a,button,div,span');
            for (const el of candidates) {
                const txt = norm(el.innerText || el.textContent);
                if (!txt) continue;
                if (txt.indexOf(norm(tabLabel)) !== -1) {
                    el.click();
                    return true;
                }
            }
        }
        return false;
    } catch (e) {
        console.error('selectDashboardTab error', e);
        return false;
    }
};

// Helper to programmatically select an option in react-select-like controls
window.__testHelpers = window.__testHelpers || {};
window.__testHelpers.selectByLabel = function(selectSelector, label){
        try{
            const root = document.querySelector(selectSelector);
            if(!root) return false;
            function tryFindAndClick(){
                const containers = Array.from(document.querySelectorAll('.Select-menu-outer, .Select-menu, [role="listbox"]'));
                for(const c of containers){
                    const opts = Array.from(c.querySelectorAll('.Select-option, [role="option"], [data-value], li, div'));
                    for(const o of opts){
                        try{
                            const txt = (o.innerText||'').trim();
                            if(!txt) continue;
                            if(txt.toLowerCase().includes(label.toLowerCase())){
                                o.scrollIntoView && o.scrollIntoView({block:'center'});
                                o.click && o.click();
                                return true;
                            }
                        }catch(e){}
                    }
                }
                return false;
            }

            try{
                const arrow = root.querySelector('.Select-arrow-zone');
                if(arrow){ arrow.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true})); arrow.click && arrow.click(); }
                const ctrl = root.querySelector('.Select-control');
                if(ctrl){ ctrl.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true})); ctrl.click && ctrl.click(); }
            }catch(e){}

            const now = Date.now();
            const deadline = now + 600;
            while(Date.now() < deadline){
                if(tryFindAndClick()) return true;
            }

            try{
                const input = root.querySelector('input');
                if(input){
                    input.focus && input.focus();
                    input.value = label;
                    input.dispatchEvent(new Event('input',{bubbles:true}));
                    input.dispatchEvent(new KeyboardEvent('keydown',{key:'a',bubbles:true}));
                    const d2 = Date.now()+400;
                    while(Date.now()<d2){ if(tryFindAndClick()) return true; }
                }
            }catch(e){}

            const all = Array.from(document.querySelectorAll('*'));
            for(const el of all){
                try{
                    if((el.innerText||'').toLowerCase().includes(label.toLowerCase())){
                        el.scrollIntoView && el.scrollIntoView({block:'center'});
                        el.click && el.click();
                        return true;
                    }
                }catch(e){}
            }

            return false;
        }catch(e){ return false; }
};
