import pytest


def find_id_in_obj(obj, target_id):
    """Recursively search for target_id in the string representation of obj."""
    try:
        s = repr(obj)
    except Exception:
        try:
            s = str(obj)
        except Exception:
            return False
    if target_id in s:
        return True
    # If obj has iterable children, search them
    try:
        if isinstance(obj, dict):
            for v in obj.values():
                if find_id_in_obj(v, target_id):
                    return True
        elif isinstance(obj, (list, tuple, set)):
            for v in obj:
                if find_id_in_obj(v, target_id):
                    return True
        else:
            # Inspect common attributes
            for attr in ('children', 'props', 'layout', '__dict__'):
                if hasattr(obj, attr):
                    val = getattr(obj, attr)
                    if find_id_in_obj(val, target_id):
                        return True
    except Exception:
        pass
    return False


def test_home_layout_contains_portfolio_value():
    """Fast smoke test: home.layout() should include the home-portfolio-value id."""
    import tabs.home as home

    layout_obj = home.layout()

    assert find_id_in_obj(layout_obj, 'home-portfolio-value'), "home-portfolio-value not found in home.layout()"
