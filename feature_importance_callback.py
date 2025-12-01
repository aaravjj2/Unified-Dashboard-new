    # Feature Importance Chart Callback
    @app.callback(
        Output(COMPONENT_IDS['explain_chart'], 'figure'),
        Input(COMPONENT_IDS['explain_store'], 'data'),
        prevent_initial_call=True
    )
    def update_explain_chart(explain_data):
        """Update feature importance chart from SHAP data."""
        if not explain_data:
            return _empty_explain_chart()
        
        try:
            # explain_data is a dict mapping forecast_id to explanation
            # Get the first explanation (or combine multiple)
            all_features = []
            all_values = []
            
            for forecast_id, explanation in explain_data.items():
                if explanation and 'features' in explanation and 'shap_values' in explanation:
                    features = explanation['features']
                    shap_values = explanation['shap_values']
                    
                    # Add to lists
                    all_features.extend(features)
                    all_values.extend(shap_values)
            
            if not all_features:
                return _empty_explain_chart()
            
            # Create bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=all_values,
                y=all_features,
                orientation='h',
                marker=dict(
                    color=all_values,
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="SHAP Value")
                ),
                text=[f"{v:.3f}" for v in all_values],
                textposition='auto',
            ))
            
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter, sans-serif", color="#e2e8f0"),
                title=dict(text="Feature Importance (SHAP Values)", x=0.5, font=dict(size=16)),
                xaxis=dict(
                    title="SHAP Value",
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.1)'
                ),
                yaxis=dict(
                    title="Feature",
                    showgrid=False
                ),
                margin=dict(l=150, r=40, t=60, b=40),
                height=300
            )
            
            return fig
            
        except Exception as e:
            logger.exception(f"Error creating explanation chart: {e}")
            return _empty_explain_chart()

