"""
Research Lab - Callbacks Module
Implements interactive behavior for research brief management.
"""

import logging
import json
from datetime import datetime
from dash import Input, Output, State, callback_context, no_update, ALL
from dash.exceptions import PreventUpdate
import requests

from .layout import create_brief_card, create_brief_detail_view
from . import components

logger = logging.getLogger(__name__)


def register_callbacks(app):
    """
    Register all Research Lab callbacks with the Dash app.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        [Output("rl-briefs-store", "data"),
         Output("rl-alert", "children"),
         Output("rl-alert", "color"),
         Output("rl-alert", "is_open")],
        [Input("rl-refresh-btn", "n_clicks"),
         Input("rl-load-demo-btn", "n_clicks")],
        prevent_initial_call=False
    )
    def load_briefs(refresh_clicks, demo_clicks):
        """Load briefs from API."""
        ctx = callback_context
        
        try:
            # Determine which button was clicked
            if ctx.triggered:
                trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
                
                if trigger_id == "rl-load-demo-btn":
                    # Load demo brief
                    response = requests.get("http://127.0.0.1:8090/api/research/demo_brief", timeout=5)
                    if response.status_code == 200:
                        demo_brief = response.json()
                        # Also create it in the system
                        create_response = requests.post(
                            "http://127.0.0.1:8090/api/research/briefs",
                            json=demo_brief,
                            timeout=5
                        )
                        if create_response.status_code == 200:
                            return (
                                [create_response.json()],
                                "Demo brief loaded successfully!",
                                "success",
                                True
                            )
            
            # Load all briefs
            response = requests.get("http://127.0.0.1:8090/api/research/briefs", timeout=5)
            if response.status_code == 200:
                briefs = response.json()
                return briefs, "", "info", False
            else:
                return [], "Failed to load briefs", "warning", True
                
        except requests.exceptions.ConnectionError:
            logger.warning("API server not reachable, using empty list")
            return [], "API server not available", "warning", False
        except Exception as e:
            logger.error(f"Error loading briefs: {e}")
            return [], f"Error: {str(e)}", "danger", True
    
    @app.callback(
        Output("rl-brief-list", "children"),
        [Input("rl-briefs-store", "data")]
    )
    def update_brief_list(briefs):
        """Update the brief list display."""
        if not briefs:
            return components.empty_brief_list()
        
        return [
            create_brief_card(
                brief_id=brief.get('id'),
                title=brief.get('title', 'Untitled'),
                summary=brief.get('summary', ''),
                tags=brief.get('tags', []),
                created_at=brief.get('created_at', ''),
                last_updated=brief.get('last_updated', '')
            )
            for brief in briefs
        ]
    
    @app.callback(
        Output("rl-selected-brief-id", "data"),
        [Input({"type": "rl-select-brief", "index": ALL}, "n_clicks")],
        [State({"type": "rl-select-brief", "index": ALL}, "id")],
        prevent_initial_call=True
    )
    def select_brief(n_clicks_list, button_ids):
        """Handle brief selection from card buttons."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        # Get the button that was clicked
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if triggered_id != '':
            try:
                # Parse the JSON id
                button_id = json.loads(triggered_id)
                if button_id.get("type") == "rl-select-brief":
                    return button_id.get("index")
            except:
                pass
        
        raise PreventUpdate
    
    @app.callback(
        Output("rl-detail-panel", "children"),
        [Input("rl-selected-brief-id", "data"),
         Input("rl-briefs-store", "data")]
    )
    def display_brief_detail(selected_id, briefs):
        """Display detailed view of selected brief."""
        if not selected_id or not briefs:
            return components.empty_detail_panel()
        
        # Find the selected brief
        brief = next((b for b in briefs if b.get('id') == selected_id), None)
        return create_brief_detail_view(brief)
    
    @app.callback(
        [Output("rl-brief-modal", "is_open"),
         Output("rl-modal-title", "children"),
         Output("rl-brief-title-input", "value"),
         Output("rl-brief-tags-input", "value"),
         Output("rl-brief-summary-input", "value"),
         Output("rl-brief-body-input", "value"),
         Output("rl-edit-brief-id", "data")],
        [Input("rl-brief-create-btn", "n_clicks"),
         Input("rl-brief-edit-btn", "n_clicks"),
         Input("rl-modal-cancel-btn", "n_clicks"),
         Input("rl-brief-save-btn", "n_clicks")],
        [State("rl-selected-brief-id", "data"),
         State("rl-briefs-store", "data"),
         State("rl-brief-title-input", "value"),
         State("rl-brief-tags-input", "value"),
         State("rl-brief-summary-input", "value"),
         State("rl-brief-body-input", "value"),
         State("rl-edit-brief-id", "data")],
        prevent_initial_call=True
    )
    def handle_brief_modal(create_clicks, edit_clicks, cancel_clicks, save_clicks,
                          selected_id, briefs, title, tags, summary, body, edit_id):
        """Handle brief creation/editing modal."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Open modal for new brief
        if trigger_id == "rl-brief-create-btn":
            return True, "New Research Brief", "", "", "", "", None
        
        # Open modal for editing
        if trigger_id == "rl-brief-edit-btn" and selected_id and briefs:
            brief = next((b for b in briefs if b.get('id') == selected_id), None)
            if brief:
                return (
                    True,
                    "Edit Research Brief",
                    brief.get('title', ''),
                    ', '.join(brief.get('tags', [])) if isinstance(brief.get('tags'), list) else brief.get('tags', ''),
                    brief.get('summary', ''),
                    brief.get('body', ''),
                    brief.get('id')
                )
        
        # Close modal
        if trigger_id in ["rl-modal-cancel-btn", "rl-brief-save-btn"]:
            # Save brief if save button was clicked
            if trigger_id == "rl-brief-save-btn" and title:
                try:
                    brief_data = {
                        'title': title,
                        'tags': [t.strip() for t in tags.split(',') if t.strip()] if tags else [],
                        'summary': summary or '',
                        'body': body or '',
                        'notes': ''
                    }
                    
                    if edit_id:
                        # Update existing brief
                        response = requests.put(
                            f"http://127.0.0.1:8090/api/research/briefs/{edit_id}",
                            json=brief_data,
                            timeout=5
                        )
                    else:
                        # Create new brief
                        response = requests.post(
                            "http://127.0.0.1:8090/api/research/briefs",
                            json=brief_data,
                            timeout=5
                        )
                    
                    if response.status_code == 200:
                        logger.info(f"Brief {'updated' if edit_id else 'created'} successfully")
                except Exception as e:
                    logger.error(f"Error saving brief: {e}")
            
            return False, "New Research Brief", "", "", "", "", None
        
        raise PreventUpdate
    
    @app.callback(
        [Output("rl-alert", "children", allow_duplicate=True),
         Output("rl-alert", "color", allow_duplicate=True),
         Output("rl-alert", "is_open", allow_duplicate=True)],
        [Input("rl-brief-delete-btn", "n_clicks")],
        [State("rl-selected-brief-id", "data")],
        prevent_initial_call=True
    )
    def delete_brief(n_clicks, selected_id):
        """Delete the selected brief."""
        if not n_clicks or not selected_id:
            raise PreventUpdate
        
        try:
            response = requests.delete(
                f"http://127.0.0.1:8090/api/research/briefs/{selected_id}",
                timeout=5
            )
            if response.status_code == 200:
                return "Brief deleted successfully", "success", True
            else:
                return "Failed to delete brief", "danger", True
        except Exception as e:
            logger.error(f"Error deleting brief: {e}")
            return f"Error: {str(e)}", "danger", True
    
    @app.callback(
        [Output("rl-alert", "children", allow_duplicate=True),
         Output("rl-alert", "color", allow_duplicate=True),
         Output("rl-alert", "is_open", allow_duplicate=True)],
        [Input("rl-notes-save-btn", "n_clicks")],
        [State("rl-selected-brief-id", "data"),
         State("rl-brief-notes-editor", "value")],
        prevent_initial_call=True
    )
    def save_notes(n_clicks, selected_id, notes):
        """Save notes for the selected brief."""
        if not n_clicks or not selected_id:
            raise PreventUpdate
        
        try:
            response = requests.put(
                f"http://127.0.0.1:8090/api/research/briefs/{selected_id}",
                json={'notes': notes or ''},
                timeout=5
            )
            if response.status_code == 200:
                return "Notes saved successfully", "success", True
            else:
                return "Failed to save notes", "danger", True
        except Exception as e:
            logger.error(f"Error saving notes: {e}")
            return f"Error: {str(e)}", "danger", True
    
    @app.callback(
        Output("rl-analysis-results", "children"),
        [Input("rl-screen-run-btn", "n_clicks"),
         Input("rl-backtest-run-btn", "n_clicks")],
        [State("rl-selected-brief-id", "data")],
        prevent_initial_call=True
    )
    def run_analysis(screen_clicks, backtest_clicks, selected_id):
        """Run screening or backtest analysis."""
        ctx = callback_context
        if not ctx.triggered or not selected_id:
            raise PreventUpdate
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        try:
            if trigger_id == "rl-screen-run-btn":
                response = requests.post(
                    "http://127.0.0.1:8090/api/research/screen",
                    json={'brief_id': selected_id},
                    timeout=10
                )
                if response.status_code == 200:
                    results = response.json()
                    return components.render_screen_results(results)
            
            elif trigger_id == "rl-backtest-run-btn":
                response = requests.post(
                    "http://127.0.0.1:8090/api/research/backtest_preview",
                    json={'brief_id': selected_id},
                    timeout=15
                )
                if response.status_code == 200:
                    results = response.json()
                    return components.render_backtest_results(results)
            
            return components.error_panel("Analysis failed")
            
        except Exception as e:
            logger.error(f"Error running analysis: {e}")
            return components.error_panel(f"Error: {str(e)}")
    
    @app.callback(
        Output("rl-brief-export-btn", "href"),
        [Input("rl-selected-brief-id", "data")]
    )
    def update_export_link(selected_id):
        """Update export download link."""
        if not selected_id:
            return "#"
        return f"/api/research/briefs/{selected_id}/export"
    
    logger.info("✓ Registered Research Lab callbacks")
