"""
Inspect Research Lab layout to find the Beginner's Guide accordion and extract its Markdown.
This doesn't require a running server and verifies the component exists and its content.
"""
import os
from financial_dashboard.tabs.research_lab_pkg import layout as rl_layout
from dash import html

OUT_MD = "/tmp/research_lab_beginner_guide.md"
OUT_HTML = "/tmp/research_lab_beginner_guide.html"

found = False
md_text = None

layout = rl_layout()
# layout is a dbc.Container; traverse children recursively

def walk(node):
    global found, md_text
    if node is None:
        return
    # Dash components are typically objects with 'children' attribute
    try:
        children = getattr(node, 'children', None)
    except Exception:
        children = None
    # If this node is a list, iterate
    if isinstance(node, (list, tuple)):
        for c in node:
            walk(c)
        return
    # Check for AccordionItem title or dcc.Markdown inside
    cls_name = node.__class__.__name__ if hasattr(node, '__class__') else str(type(node))
    # Check for dcc.Markdown by tag name
    if cls_name == 'Markdown' or 'Markdown' in cls_name:
        # node may have 'children' as markdown text
        md_text = node.children
        found = True
        return
    # For generic components, inspect children
    if children is not None:
        walk(children)

walk(layout)

if not found:
    print('❌ Beginner guide Markdown not found in Research Lab layout')
    raise SystemExit(2)

print('✅ Found Beginner guide Markdown. Writing to', OUT_MD)
os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
with open(OUT_MD, 'w', encoding='utf-8') as f:
    f.write(md_text if isinstance(md_text, str) else str(md_text))

# Optionally render to HTML for quick preview
try:
    import markdown
    html_body = markdown.markdown(md_text)
    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write('<!doctype html><html><head><meta charset="utf-8"><title>Beginner Guide</title></head><body style="background:#0a0e27;color:#fff;font-family:Arial,Helvetica,sans-serif;padding:20px;">')
        f.write(html_body)
        f.write('</body></html>')
    print('✅ Rendered HTML written to', OUT_HTML)
except Exception as e:
    print('⚠️ markdown package not available, skipped HTML render:', e)

print('Done')
