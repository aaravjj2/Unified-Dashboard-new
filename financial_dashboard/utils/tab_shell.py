"""Utility: tab_shell generator
Provides a safe, pure function that creates a minimal tab container which
can be used by tabs opting into the sandboxing model.
"""
from dash import html
import dash_bootstrap_components as dbc


def tab_shell(content_or_title, subtitle: str = '', **kwargs):
    """
    Flexible tab shell helper.

    Backwards compatible behaviour:
    - Legacy: tab_shell(title: str, subtitle: str='') -> header + placeholder
    - Rebuilds: tab_shell(layout_component, tab_name='Name') -> wraps provided layout

    This helper accepts either a title (str) or a Dash component as the
    first argument. When called with a keyword `tab_name`, it treats the
    first argument as the tab content and wraps it in a container.
    """
    tab_name = kwargs.get('tab_name')

    # If first arg is a string and no explicit tab_name provided, use legacy header
    if isinstance(content_or_title, str) and tab_name is None:
        title = content_or_title
        return dbc.Container([
            html.H3(title),
            html.P(subtitle),
            html.Div(id=f'{title}-content')
        ], fluid=True)

    # Otherwise treat first arg as content and wrap directly
    content = content_or_title
    return dbc.Container([
        content
    ], fluid=True)
