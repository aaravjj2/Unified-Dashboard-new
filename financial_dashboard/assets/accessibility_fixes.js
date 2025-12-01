// Accessibility / autofill heuristic fixer
// 1) Assign ids/names to inputs that lack them (for forms rendered without server-side ids)
// 2) Associate nearby <label> elements via for attr when possible
(function(){
  try {
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
    let created = 0;
    inputs.forEach((el, idx) => {
      if (!el.id && !el.name) {
        const gen = 'auto-field-' + idx + '-' + Math.random().toString(36).slice(2,8);
        el.id = gen;
        el.name = gen;
        created += 1;
      }
    });
    // Try to associate labels without for attributes to the nearest input within same parent
    const labels = Array.from(document.querySelectorAll('label'));
    labels.forEach((lab) => {
      if (!lab.hasAttribute('for')) {
        const input = lab.querySelector('input, textarea, select') || lab.parentElement && lab.parentElement.querySelector('input, textarea, select');
        if (input && (input.id || input.name)) {
          lab.setAttribute('for', input.id || input.name);
        } else if (input) {
          // ensure the input has id
          const gen = 'auto-field-labelled-' + Math.random().toString(36).slice(2,8);
          input.id = gen;
          lab.setAttribute('for', gen);
        }
      }
    });
    if (created>0) console.info('accessibility_fixes: created ids for', created, 'inputs');
  } catch (e) {
    console.error('accessibility_fixes error', e);
  }
})();
