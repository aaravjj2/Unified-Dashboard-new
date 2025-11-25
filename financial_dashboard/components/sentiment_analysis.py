"""
Sentiment Analysis Component for Sprint 6
Integrates Reddit, NewsAPI, and VADER for market sentiment analysis
Includes Gemini API for news summarization
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

def fetch_reddit_sentiment(ticker, subreddit='wallstreetbets', limit=100):
    """
    Fetch Reddit sentiment for a ticker
    Uses Reddit API (placeholder - implement with praw library)
    """
    # Placeholder implementation
    sentiment_scores = {
        'positive': 65,
        'neutral': 25,
        'negative': 10,
        'total_mentions': 847,
        'trending_rank': 3,
        'top_posts': [
            {'title': 'TSLA to the moon! 🚀', 'score': 5420, 'sentiment': 'positive'},
            {"title": "Why I\'m bullish on TSLA long-term", 'score': 2130, 'sentiment': 'positive'},
            {'title': 'TSLA valuation concerns', 'score': 890, 'sentiment': 'negative'}
        ]
    }
    return sentiment_scores

def fetch_news_sentiment(ticker, days=7):
    """
    Fetch news sentiment using NewsAPI
    Uses VADER for sentiment scoring
    """
    # Placeholder - implement with newsapi-python and vaderSentiment
    articles = [
        {
            'title': 'Tesla Reports Record Q4 Deliveries',
            'source': 'Reuters',
            'published_at': datetime.now() - timedelta(hours=6),
            'sentiment_score': 0.75,
            'sentiment': 'positive',
            'url': 'https://example.com/article1'
        },
        {
            'title': 'EV Competition Heats Up in 2025',
            'source': 'Bloomberg',
            'published_at': datetime.now() - timedelta(hours=12),
            'sentiment_score': -0.15,
            'sentiment': 'neutral',
            'url': 'https://example.com/article2'
        },
        {
            'title': 'Analysts Raise Price Targets on TSLA',
            'source': 'CNBC',
            'published_at': datetime.now() - timedelta(days=1),
            'sentiment_score': 0.65,
            'sentiment': 'positive',
            'url': 'https://example.com/article3'
        }
    ]
    
    avg_sentiment = np.mean([a['sentiment_score'] for a in articles])
    
    return {
        'articles': articles,
        'avg_sentiment': avg_sentiment,
        'total_articles': len(articles)
    }

def summarize_with_gemini(articles):
    """
    Use Gemini API to generate intelligent summary of news
    Placeholder - implement with google-generativeai library
    """
    summary = {
        'headline': 'TSLA shows strong momentum with record deliveries and analyst upgrades',
        'key_points': [
            'Record Q4 deliveries beat expectations by 8%',
            'Multiple analyst upgrades with avg. price target of $285',
            'Increased competition in EV space presents challenges',
            'Strong institutional buying in past week'
        ],
        'overall_tone': 'Bullish',
        'confidence': 0.78
    }
    return summary

def calculate_composite_sentiment(reddit_data, news_data):
    """Calculate composite sentiment score from multiple sources"""
    # Weighted average: Reddit 40%, News 60%
    reddit_score = (reddit_data['positive'] - reddit_data['negative']) / 100
    news_score = news_data['avg_sentiment']
    
    composite = 0.4 * reddit_score + 0.6 * news_score
    
    return {
        'score': composite,
        'normalized': (composite + 1) / 2 * 100,  # 0-100 scale
        'label': 'Bullish' if composite > 0.2 else 'Bearish' if composite < -0.2 else 'Neutral'
    }

def create_sentiment_gauge(composite_sentiment):
    """Create sentiment gauge chart"""
    score = composite_sentiment['normalized']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Sentiment: {composite_sentiment['label']}", 
               'font': {'size': 20, 'color': '#e6eef8'}},
        delta={'reference': 50, 'increasing': {'color': "#10b981"}, 
               'decreasing': {'color': "#ef4444"}},
        gauge={
            'axis': {'range': [None, 100], 'tickcolor': '#e6eef8'},
            'bar': {'color': "#60a5fa"},
            'bgcolor': "rgba(255,255,255,0.1)",
            'borderwidth': 2,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(239, 68, 68, 0.3)'},    # Bearish
                {'range': [30, 70], 'color': 'rgba(245, 158, 11, 0.3)'},  # Neutral
                {'range': [70, 100], 'color': 'rgba(16, 185, 129, 0.3)'}, # Bullish
            ]
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#e6eef8'},
        height=300,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_sentiment_timeline(ticker='TSLA', days=30):
    """Create sentiment over time chart"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    sentiment_history = np.random.uniform(-0.5, 0.8, days)  # Placeholder
    
    fig = go.Figure()
    
    colors = ['#10b981' if s > 0.2 else '#ef4444' if s < -0.2 else '#f59e0b' 
              for s in sentiment_history]
    
    fig.add_trace(go.Bar(
        x=dates,
        y=sentiment_history,
        marker_color=colors,
        name='Daily Sentiment'
    ))
    
    # Moving average
    ma_7 = pd.Series(sentiment_history).rolling(window=7).mean()
    fig.add_trace(go.Scatter(
        x=dates,
        y=ma_7,
        mode='lines',
        name='7-Day MA',
        line=dict(color='#60a5fa', width=2)
    ))
    
    fig.update_layout(
        title="Sentiment Trend (30 Days)",
        xaxis_title="Date",
        yaxis_title="Sentiment Score",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#e6eef8',
        hovermode='x unified',
        height=350,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)', 
                     zeroline=True, zerolinecolor='rgba(255,255,255,0.3)')
    
    return fig

def create_sentiment_analysis_layout():
    """Create Sentiment Analysis layout"""
    ticker = 'TSLA'  # Default ticker
    
    reddit_data = fetch_reddit_sentiment(ticker)
    news_data = fetch_news_sentiment(ticker)
    composite = calculate_composite_sentiment(reddit_data, news_data)
    summary = summarize_with_gemini(news_data['articles'])
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-comments me-2"),
                    "Sentiment Analysis"
                ], className="mb-3"),
                html.P(
                    "Market sentiment analysis powered by Reddit, news sources, and AI. "
                    "Gauge retail and institutional sentiment in real-time.",
                    className="text-muted"
                )
            ])
        ]),
        
        # Ticker Selection
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Ticker"),
                    dbc.Input(
                        id='sentiment-ticker-input',
                        placeholder='Enter ticker...',
                        value=ticker,
                        type='text'
                    ),
                    dbc.Button("Analyze", id='sentiment-analyze-btn', color="primary")
                ])
            ], md=6)
        ], className="mb-4"),
        
        # Sentiment Gauge and Stats
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(
                            id='sentiment-gauge',
                            figure=create_sentiment_gauge(composite),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=4),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Reddit Sentiment (r/wallstreetbets)"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.H3(f"{reddit_data['positive']}%", 
                                           className="text-success mb-0"),
                                    html.Small("Positive", className="text-muted")
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div([
                                    html.H3(f"{reddit_data['neutral']}%", 
                                           className="text-warning mb-0"),
                                    html.Small("Neutral", className="text-muted")
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div([
                                    html.H3(f"{reddit_data['negative']}%", 
                                           className="text-danger mb-0"),
                                    html.Small("Negative", className="text-muted")
                                ])
                            ], width=4)
                        ]),
                        html.Hr(),
                        html.Small([
                            html.Strong(f"{reddit_data['total_mentions']} "),
                            "total mentions • Trending #",
                            html.Strong(str(reddit_data['trending_rank']))
                        ], className="text-muted")
                    ])
                ])
            ], md=4),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("News Sentiment (7 days)"),
                    dbc.CardBody([
                        html.Div([
                            html.H3(
                                f"{news_data['avg_sentiment']:+.2f}",
                                className="mb-2",
                                style={'color': '#10b981' if news_data['avg_sentiment'] > 0 
                                       else '#ef4444'}
                            ),
                            html.Small("Average Sentiment Score", className="text-muted d-block"),
                            html.Hr(),
                            html.Small([
                                html.Strong(str(news_data['total_articles'])),
                                " articles analyzed"
                            ], className="text-muted")
                        ])
                    ])
                ])
            ], md=4)
        ], className="mb-4"),
        
        # AI Summary from Gemini
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-brain me-2"),
                        "AI Summary (Powered by Gemini)"
                    ]),
                    dbc.CardBody([
                        html.H5(summary['headline'], className="mb-3"),
                        html.H6("Key Points:", className="mb-2"),
                        html.Ul([
                            html.Li(point) for point in summary['key_points']
                        ]),
                        dbc.Badge(
                            f"{summary['overall_tone']} • {summary['confidence']*100:.0f}% confidence",
                            color="success" if summary['overall_tone'] == 'Bullish' else 'danger',
                            className="mt-2"
                        )
                    ])
                ])
            ], md=12)
        ], className="mb-4"),
        
        # Sentiment Timeline
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Sentiment Trend"),
                    dbc.CardBody([
                        dcc.Graph(
                            id='sentiment-timeline',
                            figure=create_sentiment_timeline(ticker),
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ], md=12)
        ], className="mb-4"),
        
        # Top Reddit Posts
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Top Reddit Posts"),
                    dbc.CardBody([
                        dbc.ListGroup([
                            dbc.ListGroupItem([
                                html.Div([
                                    html.Strong(post['title']),
                                    dbc.Badge(
                                        post['sentiment'].capitalize(),
                                        color='success' if post['sentiment'] == 'positive' 
                                              else 'danger',
                                        className="ms-2"
                                    )
                                ]),
                                html.Small(f"↑ {post['score']} upvotes", className="text-muted")
                            ])
                            for post in reddit_data['top_posts']
                        ])
                    ])
                ])
            ], md=6),
            
            # Recent News
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Recent News"),
                    dbc.CardBody([
                        dbc.ListGroup([
                            dbc.ListGroupItem([
                                html.Div([
                                    html.Strong(article['title']),
                                    dbc.Badge(
                                        f"{article['sentiment_score']:+.2f}",
                                        color='success' if article['sentiment_score'] > 0 
                                              else 'danger',
                                        className="ms-2"
                                    )
                                ]),
                                html.Small([
                                    article['source'],
                                    " • ",
                                    article['published_at'].strftime("%b %d, %I:%M %p")
                                ], className="text-muted")
                            ], href=article['url'], target="_blank", action=True)
                            for article in news_data['articles']
                        ])
                    ])
                ])
            ], md=6)
        ])
    ], fluid=True)

def register_sentiment_callbacks(app):
    """Register sentiment analysis callbacks"""
    from dash import Output, Input, State
    
    @app.callback(
        [Output('sentiment-gauge', 'figure'),
         Output('sentiment-timeline', 'figure')],
        [Input('sentiment-analyze-btn', 'n_clicks')],
        [State('sentiment-ticker-input', 'value')],
        prevent_initial_call=True
    )
    def update_sentiment_analysis(n_clicks, ticker):
        """Update sentiment analysis for ticker"""
        reddit_data = fetch_reddit_sentiment(ticker)
        news_data = fetch_news_sentiment(ticker)
        composite = calculate_composite_sentiment(reddit_data, news_data)
        
        return (
            create_sentiment_gauge(composite),
            create_sentiment_timeline(ticker)
        )
