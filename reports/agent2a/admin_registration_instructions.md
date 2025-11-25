Admin Diagnostics Registration Instructions

To register the admin diagnostics blueprint into your Flask server (do this only after coordinating with Agent-1A):

In `financial_dashboard/app.py` after server creation add:

```python
from api.admin_diagnostics import admin_bp
server.register_blueprint(admin_bp)
```

This will enable endpoints:
- `/admin/callback_map`
- `/admin/tab_health/<tab>`

Do not register this automatically — coordinate to avoid exposing sensitive internals.
