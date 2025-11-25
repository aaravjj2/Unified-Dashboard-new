# Design Document

## Overview

The dashboard rebuild addresses critical architectural issues including circular imports, React rendering errors, and improper initialization sequences. The design implements a clean separation of concerns with explicit initialization order, proper module boundaries, and comprehensive error handling. The system will launch on port 8090 with all tabs functional and zero React console errors.

## Architecture

### Three-Layer Architecture

**Layer 1: Application Factory (`app.py`)**
- Creates Flask server instance
- Registers API endpoints
- Creates Dash application
- Configures middleware and error handlers
- Returns configured app (does NOT set layout or register callbacks)

**Layer 2: Layout Builder (`index.py`)**
- Defines `create_layout()` function
- Loads tab modules dynamically
- Assembles complete dashboard layout
- Returns layout structure (does NOT register callbacks)

**Layer 3: Callback Registry (`callbacks.py`)**
- Registers all dashboard callbacks
- Validates callback uniqueness
- Handles callback deduplication
- Logs callback registration summary

### Initialization Sequence

```
1. app.py: create_app() → Flask + Dash instance
2. app.py: Import index module (loads tabs)
3. app.py: Call index.create_layout() → layout structure
4. app.py: Set app.layout = layout
5. app.py: Import callbacks module
6. callbacks.py: Register all callbacks
7. app.py: Return configured app
8. run_dashboard.py: app.run_server(port=8090)
```

### Module Dependency Graph

```
run_dashboard.py
    ↓
app.py (creates app)
    ↓
index.py (creates layout)
    ↓
tabs/* (individual tab modules)
    ↓
callbacks.py (registers callbacks)
```

**Key Design Decision:** No circular imports. Each module imports only from layers below it.

## Components and Interfaces

### 1. Application Factory (`app.py`)

```python
def create_app() -> dash.Dash:
    """
    Create and configure Dash application.
    
    Returns:
        Configured Dash app with layout and callbacks registered
    """
    # 1. Create Flask server
    server = Flask(__name__)
    
    # 2. Register API endpoints
    register_api_endpoints(server)
    
    # 3. Create Dash app
    app = dash.Dash(
        __name__,
        server=server,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    
    # 4. Import and set layout
    from . import index
    app.layout = index.create_layout()
    
    # 5. Register callbacks
    from . import callbacks
    callbacks.register_all_callbacks(app, index.loaded_tabs)
    
    return app
```

### 2. Layout Builder (`index.py`)

```python
def create_layout() -> dbc.Container:
    """
    Create complete dashboard layout.
    
    Returns:
        Dashboard layout with all tabs
    """
    # Load tab modules
    loaded_tabs = load_tab_modules()
    
    # Create tab components
    tabs = []
    for tab_id in ENABLED_TABS:
        if tab_id in loaded_tabs:
            tab_content = loaded_tabs[tab_id]['module'].layout()
            tabs.append(dbc.Tab(
                tab_content,
                label=loaded_tabs[tab_id]['name'],
                tab_id=tab_id
            ))
    
    # Assemble layout
    return dbc.Container([
        create_navbar(),
        dbc.Tabs(tabs, id="dashboard-tabs"),
        create_hidden_stores()
    ], fluid=True)

def load_tab_modules() -> dict:
    """
    Dynamically load all tab modules.
    
    Returns:
        Dictionary mapping tab_id to module info
    """
    loaded = {}
    for tab_config in TAB_CONFIG:
        try:
            module = importlib.import_module(
                f"financial_dashboard.tabs.{tab_config['id']}"
            )
            loaded[tab_config['id']] = {
                'module': module,
                'name': tab_config['name']
            }
        except Exception as e:
            logger.error(f"Failed to load {tab_config['id']}: {e}")
    return loaded
```

### 3. Callback Registry (`callbacks.py`)

```python
def register_all_callbacks(app: dash.Dash, loaded_tabs: dict) -> int:
    """
    Register all dashboard callbacks.
    
    Args:
        app: Dash application instance
        loaded_tabs: Dictionary of loaded tab modules
    
    Returns:
        Number of callbacks registered
    """
    callback_count = 0
    seen_outputs = set()
    
    # Register tab-specific callbacks
    for tab_id, tab_info in loaded_tabs.items():
        if hasattr(tab_info['module'], 'register_callbacks'):
            try:
                count = tab_info['module'].register_callbacks(app)
                callback_count += count
                logger.info(f"Registered {count} callbacks for {tab_id}")
            except Exception as e:
                logger.error(f"Failed to register callbacks for {tab_id}: {e}")
    
    # Validate no duplicate outputs
    validate_callback_uniqueness(app)
    
    return callback_count

def validate_callback_uniqueness(app: dash.Dash):
    """
    Validate that no callbacks have duplicate output targets.
    
    Raises:
        ValueError: If duplicate outputs are detected
    """
    outputs = {}
    for callback_id, callback_info in app.callback_map.items():
        for output in callback_info['outputs']:
            output_key = f"{output['id']}.{output['property']}"
            if output_key in outputs:
                logger.warning(
                    f"Duplicate output detected: {output_key} "
                    f"(callbacks: {outputs[output_key]}, {callback_id})"
                )
            outputs[output_key] = callback_id
```

### 4. Dashboard Runner (`run_dashboard.py`)

```python
def main():
    """Run the dashboard server on port 8090."""
    from financial_dashboard.app import create_app
    
    app = create_app()
    
    try:
        logger.info("Starting dashboard on port 8090...")
        app.run_server(
            host='0.0.0.0',
            port=8090,
            debug=False
        )
    except OSError as e:
        if 'Address already in use' in str(e):
            logger.error(
                "Port 8090 is already in use. "
                "Stop the existing process or use a different port."
            )
        else:
            raise

if __name__ == '__main__':
    main()
```

## Data Models

### Tab Configuration Model

```python
@dataclass
class TabConfig:
    id: str              # Unique tab identifier (e.g., 'options_lab')
    name: str            # Display name (e.g., '💹 Options Lab')
    module_path: str     # Python module path
    enabled: bool = True # Whether tab is active
```

### Callback Registration Result

```python
@dataclass
class CallbackRegistrationResult:
    total_callbacks: int
    successful: int
    failed: int
    duplicate_outputs: List[str]
    errors: List[Dict[str, str]]  # {'tab_id': str, 'error': str}
```

### Layout Validation Result

```python
@dataclass
class LayoutValidationResult:
    is_valid: bool
    tab_count: int
    missing_tabs: List[str]
    invalid_components: List[str]
    errors: List[str]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: No React rendering errors

*For any* dashboard load, the browser console should contain zero React errors (no "Objects are not valid as a React child" errors, no minified React errors)
**Validates: Requirements 2.1, 2.3, 2.5**

### Property 2: Valid React elements only

*For any* component in the layout, all children props should be valid React elements (strings, numbers, or Dash components), never raw Python objects with {props, type, namespace} structure
**Validates: Requirements 2.2**

### Property 3: Invalid objects are sanitized

*For any* invalid object passed to a component, the layout system should sanitize it to a valid React element before rendering
**Validates: Requirements 2.4**

### Property 4: No duplicate callback outputs

*For any* set of registered callbacks, no two callbacks should target the same output (component_id, property) pair
**Validates: Requirements 3.1, 3.3**

### Property 5: Callback deduplication works

*For any* set of callbacks with duplicate outputs, the deduplication system should keep only one callback per output target
**Validates: Requirements 3.2**

### Property 6: Tabs generate content synchronously

*For any* tab module, calling its layout() function should return content immediately without async operations
**Validates: Requirements 5.2**

### Property 7: All tabs load without errors

*For any* tab in the ENABLED_TABS list, loading the tab module should succeed without ImportError or other exceptions
**Validates: Requirements 7.1**

### Property 8: Tab switching displays correct content

*For any* tab, clicking on it should display that tab's content and no other tab's content
**Validates: Requirements 7.2**

### Property 9: Tabs render without errors

*For any* tab, rendering its content should produce zero React console errors
**Validates: Requirements 7.3**

### Property 10: Errors are logged with details

*For any* error that occurs, the system should log it with a detailed message including error type, location, and stack trace
**Validates: Requirements 8.1**

## Error Handling

### Import Error Handling

**Strategy:** Graceful degradation with clear error messages

```python
def load_tab_modules():
    loaded = {}
    for tab_config in TAB_CONFIG:
        try:
            module = import_tab(tab_config)
            loaded[tab_config['id']] = module
        except ImportError as e:
            logger.error(
                f"Failed to import {tab_config['id']}: {e}\n"
                f"Tab will be disabled. Check dependencies."
            )
        except Exception as e:
            logger.error(
                f"Unexpected error loading {tab_config['id']}: {e}\n"
                f"{traceback.format_exc()}"
            )
    return loaded
```

### React Rendering Error Handling

**Strategy:** Component sanitization before rendering

```python
def sanitize_component(component):
    """
    Sanitize component to ensure valid React rendering.
    
    Converts invalid objects to valid Dash components.
    """
    if isinstance(component, dict):
        # Check for invalid {props, type, namespace} structure
        if 'props' in component and 'type' in component:
            # This is a raw Dash component object, not a valid child
            logger.warning(f"Sanitizing invalid component: {component.get('type')}")
            # Convert to proper Dash component
            return html.Div(f"[Component: {component.get('type')}]")
    return component
```

### Callback Registration Error Handling

**Strategy:** Log and continue with remaining callbacks

```python
def register_tab_callbacks(app, tab_module):
    try:
        count = tab_module.register_callbacks(app)
        return count
    except Exception as e:
        logger.error(
            f"Failed to register callbacks for {tab_module.__name__}: {e}\n"
            f"{traceback.format_exc()}\n"
            f"Tab functionality may be limited."
        )
        return 0
```

### Port Binding Error Handling

**Strategy:** Clear error message with resolution steps

```python
def start_server(app, port=8090):
    try:
        app.run_server(host='0.0.0.0', port=port)
    except OSError as e:
        if 'Address already in use' in str(e):
            logger.error(
                f"ERROR: Port {port} is already in use.\n\n"
                f"Resolution steps:\n"
                f"1. Find the process: lsof -i :{port}\n"
                f"2. Kill the process: kill -9 <PID>\n"
                f"3. Or use a different port: PORT=8091 python run_dashboard.py"
            )
            sys.exit(1)
        raise
```

## Testing Strategy

### Unit Tests

**Component Sanitization Tests:**
- Test sanitization of invalid {props, type, namespace} objects
- Test that valid components pass through unchanged
- Test sanitization of nested component structures

**Module Loading Tests:**
- Test successful loading of all tab modules
- Test graceful handling of missing modules
- Test error messages for import failures

**Callback Registration Tests:**
- Test callback counting
- Test duplicate detection
- Test error handling for failed registrations

### Integration Tests

**Full Application Startup:**
- Test complete initialization sequence
- Test layout creation with all tabs
- Test callback registration
- Test server binding to port 8090

**Tab Functionality:**
- Test each tab loads without errors
- Test tab switching works correctly
- Test tab content renders properly

### Browser Tests

**React Rendering:**
- Test dashboard loads without console errors
- Test no "Objects are not valid as a React child" errors
- Test no minified React errors
- Test all tabs render correctly

**User Interactions:**
- Test tab switching
- Test callback functionality
- Test error boundaries work

## Implementation Approach

### Phase 1: Clean Architecture Setup

1. Create new `run_dashboard.py` entry point
2. Refactor `app.py` to be pure application factory
3. Refactor `index.py` to export `create_layout()` function
4. Create new `callbacks.py` for centralized callback registration
5. Remove all circular imports

### Phase 2: Layout System Rebuild

1. Implement `create_layout()` with proper tab loading
2. Add component sanitization layer
3. Implement error boundaries for tab content
4. Add layout validation
5. Test layout generation

### Phase 3: Callback System Rebuild

1. Implement centralized callback registration
2. Add duplicate output detection
3. Add callback validation
4. Implement error handling for failed callbacks
5. Test callback registration

### Phase 4: Port Configuration

1. Update server configuration for port 8090
2. Add port conflict detection
3. Add clear error messages
4. Test server startup

### Phase 5: Integration and Testing

1. Test complete initialization sequence
2. Test all tabs load and render
3. Test React console is clean
4. Test callbacks work correctly
5. Validate no circular imports

## Key Design Decisions

### Decision 1: Three-Layer Architecture

**Rationale:** Separating app creation, layout building, and callback registration eliminates circular imports and makes the initialization sequence explicit and testable.

**Alternative Considered:** Monolithic initialization in a single file. Rejected because it makes testing difficult and doesn't solve circular import issues.

### Decision 2: Explicit Initialization Sequence

**Rationale:** Having a clear, documented initialization order (app → layout → callbacks) makes the system predictable and debuggable.

**Alternative Considered:** Lazy initialization with decorators. Rejected because it makes the order implicit and harder to reason about.

### Decision 3: Component Sanitization Layer

**Rationale:** Proactively sanitizing components before rendering prevents React errors and provides clear error messages.

**Alternative Considered:** Reactive error boundaries. Rejected because they only catch errors after they occur, not prevent them.

### Decision 4: Centralized Callback Registry

**Rationale:** Having all callbacks registered in one place makes duplicate detection and validation straightforward.

**Alternative Considered:** Distributed callback registration in each tab. Rejected because it makes duplicate detection difficult.

### Decision 5: Port 8090 Configuration

**Rationale:** Using a non-standard port (not 8050) avoids conflicts with other Dash applications and makes the dashboard easily identifiable.

**Alternative Considered:** Dynamic port selection. Rejected because it makes the dashboard URL unpredictable.
