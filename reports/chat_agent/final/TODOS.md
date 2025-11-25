# TODO - RAG Chat Assistant Remaining Work

**Priority:** HIGH - UI Integration & Testing  
**Estimated Effort:** 4-6 hours for completion

---

## CRITICAL: UI Callback Wiring (2-3 hours)

### File: `financial_dashboard/components/chatbot_ui.py` or create `financial_dashboard/callbacks/chatbot_callbacks.py`

**Required Callbacks:**

### 1. Chat Message Submit
```python
@app.callback(
    Output("chatbot-messages", "children"),
    Input("chatbot-send-btn", "n_clicks"),
    State("chatbot-input", "value"),
    State("chatbot-messages", "children"),
    State("chat-toggle-context", "value"),  # Add this checkbox to UI
    prevent_initial_call=True
)
def handle_chat_submit(n_clicks, message, current_messages, include_context):
    """
    Send message to /api/chat/query and display response
    
    Steps:
    1. Validate message not empty
    2. Add user message bubble to chat
    3. Call fetch('/api/chat/query', ...) via clientside callback or requests
    4. Parse response
    5. Add bot message bubble with answer
    6. If action_suggestion present, display action card
    7. Return updated messages list
    """
    pass
```

### 2. Action Confirmation Modal
```python
@app.callback(
    Output("action-confirmation-modal", "is_open"),
    Output("action-suggestion-display", "children"),
    Input("chat-response-contains-action", "data"),  # Hidden store
    prevent_initial_call=True
)
def show_action_confirmation(action_data):
    """
    Display confirmation modal when action suggested
    
    Shows:
    - Action type
    - Payload details (symbol, qty, etc.)
    - Confirm/Cancel buttons
    """
    pass

@app.callback(
    Output("action-execution-result", "children"),
    Input("chat-action-confirm-yes", "n_clicks"),
    State("pending-action-store", "data"),
    prevent_initial_call=True
)
def execute_confirmed_action(n_clicks, action_data):
    """
    Execute action after user confirms
    
    Calls: POST /api/chat/execute_action
    """
    pass
```

### 3. Context Toggle
```python
# Add to chatbot UI:
dbc.Checkbox(
    id="chat-toggle-context",
    label="Include current page context",
    value=True
)

# In callback, construct tab_context:
if include_context:
    tab_context = {
        "tab": get_active_tab(),  # From URL or store
        "ticker": get_current_ticker(),  # From store
    }
```

---

## UI Component Updates

### Add to `chatbot_ui.py`:

```python
# Action suggestion card component
def create_action_card(action_data):
    return dbc.Card([
        dbc.CardHeader("🤖 Action Suggestion"),
        dbc.CardBody([
            html.H5(action_data['action']),
            html.Pre(json.dumps(action_data['payload'], indent=2)),
            html.P(f"Confidence: {action_data.get('confidence', 'N/A')}"),
            dbc.ButtonGroup([
                dbc.Button("✅ Confirm", id="chat-action-confirm-yes", color="success"),
                dbc.Button("❌ Cancel", id="chat-action-confirm-no", color="danger")
            ])
        ])
    ], id="chat-action-suggestion-card", color="warning")
```

---

## PHASE 7: Playwright Tests (2-3 hours)

### File: `tests/playwright/test_chat_rag.py`

```python
def test_chat_text_color(page):
    """Verify chat text is black (#000)"""
    page.goto("http://localhost:8050")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    
    # Wait for chat to be visible
    page.wait_for_selector("#chatbot-messages-container")
    
    # Get computed color
    color = page.eval_on_selector(
        "#chatbot-messages",
        "el => window.getComputedStyle(el).color"
    )
    
    # Assert black
    assert color == "rgb(0, 0, 0)", f"Chat text color is {color}, expected rgb(0, 0, 0)"
    
    # Screenshot
    page.screenshot(path="reports/chat_agent/screenshots/chat_color_verify.png")


def test_rag_query_with_sources(page):
    """Test RAG query returns sources"""
    page.goto("http://localhost:8050")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    
    # Type query
    page.fill("#chatbot-input", "What is the volatility for AAPL?")
    
    # Send
    page.click("#chatbot-send-btn")
    
    # Wait for response
    page.wait_for_selector("[id^='chat-response-']", timeout=10000)
    
    # Verify response contains source citation
    response_text = page.text_content("[id^='chat-response-']")
    assert "[Source" in response_text or "vol_surface_aapl" in response_text
    
    # Screenshot
    page.screenshot(path="reports/chat_agent/screenshots/rag_query_result.png")


def test_action_suggestion_flow(page):
    """Test action suggestion -> confirmation -> execution"""
    page.goto("http://localhost:8050")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    
    # Query that triggers action
    page.fill("#chatbot-input", "Create a paper order for 1 share of AAPL at market price")
    page.click("#chatbot-send-btn")
    
    # Wait for action card
    page.wait_for_selector("#chat-action-suggestion-card", timeout=10000)
    
    # Verify action details
    action_text = page.text_content("#chat-action-suggestion-card")
    assert "AAPL" in action_text
    assert "buy" in action_text.lower()
    
    # Confirm action
    page.click("#chat-action-confirm-yes")
    
    # Wait for execution result
    page.wait_for_selector("[id^='action-execution-result']", timeout=5000)
    
    # Verify success
    result_text = page.text_content("[id^='action-execution-result']")
    assert "success" in result_text.lower() or "submitted" in result_text.lower()
    
    # Screenshot
    page.screenshot(path="reports/chat_agent/screenshots/action_executed.png")
```

---

## PHASE 8: Observability (1 hour)

### Admin Endpoints

**File:** `financial_dashboard/api/chat.py`

```python
@chat_api.route('/admin/last_queries', methods=['GET'])
def admin_last_queries():
    """Get recent queries for debugging"""
    limit = request.args.get('limit', 20, type=int)
    
    # Read from audit log or in-memory cache
    # Return recent queries with metadata
    pass


@chat_api.route('/admin/health_detail', methods=['GET'])
def admin_health_detail():
    """Detailed health check with diagnostics"""
    index = get_index()
    generator = get_generator()
    
    return jsonify({
        "index": {
            "size": index.size(),
            "has_faiss": index.has_faiss,
            "metadata_count": len(index._metadata),
            "last_save": os.path.getmtime(index.index_path) if index.index_path.exists() else None
        },
        "generator": generator.health_check(),
        "fixtures_available": os.path.exists("reports/chat_agent/fixtures"),
        "audit_log_size": os.path.getsize("reports/chat_agent/logs/action_audit.log") if os.path.exists("reports/chat_agent/logs/action_audit.log") else 0
    })
```

---

## Enhancement: Streaming Responses (Optional, 2 hours)

### Server-Sent Events for streaming

**File:** `financial_dashboard/api/chat.py`

```python
@chat_api.route('/query_stream', methods=['POST'])
def query_stream():
    """Streaming query endpoint using SSE"""
    def generate():
        data = request.get_json()
        query = data['query']
        
        # Get RAG orchestrator
        rag = get_rag()
        
        # Retrieve chunks
        chunks = rag.retrieve(query)
        
        # Stream retrieval progress
        yield f"data: {json.dumps({'type': 'retrieval', 'chunks': len(chunks)})}\n\n"
        
        # Stream generation tokens
        for token in rag.generator.complete(query, stream=True):
            yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')
```

---

## Documentation Updates

### File: `docs/chat/README.md` (Create)

```markdown
# RAG Chat Assistant Documentation

## Overview
Local RAG-based chat assistant with FAISS vector retrieval and gpt4all generator.

## Architecture
[Diagram of retrieval → generation flow]

## API Reference
[Document all endpoints with examples]

## Configuration
[Environment variables, model selection, etc.]

## Troubleshooting
[Common issues and solutions]
```

---

## Testing Checklist

- [ ] Unit tests for chunker (various text sizes, edge cases)
- [ ] Unit tests for FAISS index (add, search, save/load)
- [ ] Unit tests for action executor (validation, audit logging)
- [ ] Integration test: full RAG query flow
- [ ] Playwright: CSS color validation
- [ ] Playwright: Query with sources
- [ ] Playwright: Action suggestion → confirmation → execution
- [ ] Load test: concurrent queries
- [ ] Security test: Live trading rejection
- [ ] Security test: Unconfirmed action rejection

---

## Deployment Considerations

### Production Checklist

- [ ] Install production-grade models (larger than orca-mini-3b)
- [ ] Enable GPU acceleration (faiss-gpu, CUDA)
- [ ] Configure proper logging (ELK stack, CloudWatch, etc.)
- [ ] Set up monitoring (Prometheus metrics for query latency, retrieval quality)
- [ ] Implement rate limiting on API endpoints
- [ ] Add authentication/authorization to admin endpoints
- [ ] Configure CORS properly
- [ ] Set up backup/restore for FAISS index
- [ ] Document disaster recovery procedures

### Performance Tuning

- [ ] Cache frequently-accessed chunks
- [ ] Pre-warm model at startup
- [ ] Use connection pooling for API calls
- [ ] Implement query result caching
- [ ] Optimize chunk size based on domain (may need smaller/larger than 512)
- [ ] Fine-tune embedding model on financial texts

---

## Priority Order

1. **CRITICAL:** UI callback wiring (enables end-to-end testing)
2. **HIGH:** Playwright tests with CSS validation
3. **MEDIUM:** Observability/admin endpoints
4. **LOW:** Streaming responses (nice-to-have)
5. **ONGOING:** Documentation updates

---

**Estimated Total Time to Complete:** 4-6 hours  
**Blocker:** None - all dependencies installed, backend ready  
**Next Action:** Wire `chatbot-send-btn` callback to `/api/chat/query`
