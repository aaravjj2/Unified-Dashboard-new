import json
from collections import defaultdict


def _collect(node, ids, texts):
    # Handle None
    if node is None:
        return

    # Basic primitives
    if isinstance(node, str):
        texts.append(node)
        return
    if isinstance(node, (int, float, bool)):
        return

    # If node is a list/tuple, recurse
    if isinstance(node, (list, tuple)):
        for child in node:
            _collect(child, ids, texts)
        return

    # If node is a dict, check for id and recurse values
    if isinstance(node, dict):
        _id = node.get('id')
        if _id is not None:
            try:
                ids.append(json.dumps(_id, sort_keys=True))
            except Exception:
                ids.append(str(_id))
        for v in node.values():
            _collect(v, ids, texts)
        return

    # Otherwise, assume it's a Dash component-like object with .id and .children
    try:
        comp_id = getattr(node, 'id', None)
        if comp_id is not None:
            try:
                ids.append(json.dumps(comp_id, sort_keys=True))
            except Exception:
                ids.append(str(comp_id))
    except Exception:
        pass

    # Children attribute
    try:
        children = getattr(node, 'children', None)
        if children is not None:
            _collect(children, ids, texts)
    except Exception:
        pass


def test_layout_has_no_duplicate_ids_and_includes_research():
    # Import app lazily to avoid side-effects at collection time
    from financial_dashboard.app import app

    layout = app.layout

    ids = []
    texts = []
    _collect(layout, ids, texts)

    # Check duplicates
    counts = defaultdict(int)
    for i in ids:
        counts[i] += 1

    duplicates = [k for k, v in counts.items() if v > 1]
    assert not duplicates, f"Found duplicate component ids in layout: {duplicates}"

    # Verify Research Lab header exists in rendered layout text snippets
    found = any(('Research Lab' in str(t) for t in texts))
    assert found, "Research Lab header not found in app layout"
