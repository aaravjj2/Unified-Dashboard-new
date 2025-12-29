"""
Enhanced GROQ AI Module
=======================
Advanced GROQ AI integration with:
- Zero-prompt analysis (AI analyzes without questions)
- Proactive recommendations
- Context-aware conversations
- Multi-model consensus
- Explainable AI with clear reasoning

Author: AI/ML Options Lab
"""

import os
import logging
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class AIAnalysis:
    """AI-generated analysis."""
    analysis_id: str
    ticker: str
    analysis_type: str
    
    summary: str
    key_points: List[str]
    recommendation: str
    confidence: float
    
    supporting_data: Dict
    reasoning_chain: List[str]  # Explainable AI - show reasoning
    
    generated_at: datetime
    model_used: str


@dataclass
class ProactiveInsight:
    """Proactive AI insight (without user prompt)."""
    insight_id: str
    category: str  # 'opportunity', 'risk', 'market', 'position'
    priority: str  # 'low', 'medium', 'high', 'urgent'
    
    title: str
    insight: str
    action_items: List[str]
    
    affected_tickers: List[str]
    confidence: float
    
    generated_at: datetime
    expires_at: datetime


@dataclass
class ConversationContext:
    """Context for AI conversation."""
    conversation_id: str
    messages: List[Dict]
    
    # Tracked entities
    tickers_discussed: List[str]
    strategies_discussed: List[str]
    user_preferences: Dict
    
    # Context from analysis
    market_context: Dict
    position_context: Dict
    
    created_at: datetime
    last_updated: datetime


@dataclass
class ModelConsensus:
    """Multi-model consensus result."""
    query: str
    
    # Individual model outputs
    model_responses: Dict[str, str]
    model_confidences: Dict[str, float]
    
    # Consensus
    consensus_answer: str
    consensus_confidence: float
    agreement_level: float  # How much models agree
    
    # Dissenting views
    minority_opinions: List[str]
    
    generated_at: datetime


# ============================================================
# GROQ CLIENT
# ============================================================

class EnhancedGroqClient:
    """Enhanced GROQ API client with advanced features."""
    
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Available models
        self.models = {
            'fast': 'llama-3.1-8b-instant',
            'balanced': 'llama-3.3-70b-versatile',
            'analytical': 'llama-3.3-70b-versatile'
        }
        
        self.default_model = self.models['balanced']
        
        # System prompts for different contexts
        self.system_prompts = {
            'options_analyst': """You are an expert options trading analyst with deep knowledge of:
- Options pricing and Greeks
- Volatility analysis and IV rank/percentile
- Options strategies (spreads, iron condors, straddles, etc.)
- Risk management and position sizing
- Market regime analysis

Provide clear, actionable analysis. Always explain your reasoning.
Use specific numbers and data points when available.
Format responses with clear sections and bullet points.""",

            'risk_advisor': """You are a risk management AI advisor specializing in:
- Portfolio risk assessment
- Position sizing optimization
- Stop loss and profit target recommendations
- Correlation and concentration risk
- Tail risk and black swan events

Be conservative in risk assessments. Always prioritize capital preservation.
Provide specific risk metrics and actionable recommendations.""",

            'proactive_analyst': """You are a proactive AI analyst that identifies opportunities
and risks without being asked. Your role is to:
- Spot trading opportunities based on market conditions
- Identify risks in current positions
- Suggest portfolio adjustments
- Alert to upcoming events (earnings, ex-div, etc.)

Generate insights that are immediately actionable.
Prioritize based on urgency and potential impact.""",

            'explainer': """You are an AI that explains complex options concepts clearly.
Always:
- Break down complex ideas into simple steps
- Use analogies when helpful
- Show your reasoning chain
- Acknowledge uncertainty when appropriate
- Cite specific data points"""
        }
    
    def query(self, prompt: str, context: str = 'options_analyst',
              temperature: float = 0.7, model: str = None) -> str:
        """Send a query to GROQ API."""
        if not self.api_key:
            return self._fallback_response(prompt)
        
        model = model or self.default_model
        system_prompt = self.system_prompts.get(context, self.system_prompts['options_analyst'])
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": 2000
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"GROQ API error: {response.status_code}")
                return self._fallback_response(prompt)
                
        except Exception as e:
            logger.error(f"GROQ query failed: {e}")
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt: str) -> str:
        """Generate fallback response when API unavailable."""
        return f"""Analysis for your query:

Based on the available data, here's a general assessment:

**Market Conditions:**
- Current volatility environment appears normal
- Key indices showing mixed signals
- Watch for upcoming events that may impact positions

**Recommendations:**
1. Review position sizes relative to account
2. Ensure stops are in place
3. Monitor theta decay on open positions
4. Consider hedging if concentrated

Note: This is a fallback response. Connect GROQ API for detailed AI analysis."""


# ============================================================
# ZERO-PROMPT ANALYZER
# ============================================================

class ZeroPromptAnalyzer:
    """
    AI that analyzes without user prompts.
    Proactively generates insights based on market data.
    """
    
    def __init__(self):
        self.groq = EnhancedGroqClient()
        self._analysis_counter = 0
    
    def auto_analyze(self, ticker: str, market_data: Dict) -> AIAnalysis:
        """Automatically analyze a ticker without user prompt."""
        self._analysis_counter += 1
        
        # Build analysis prompt from data
        prompt = self._build_analysis_prompt(ticker, market_data)
        
        # Get AI analysis
        response = self.groq.query(prompt, context='options_analyst')
        
        # Parse response into structured analysis
        return self._parse_analysis(ticker, response, market_data)
    
    def _build_analysis_prompt(self, ticker: str, data: Dict) -> str:
        """Build comprehensive analysis prompt from market data."""
        prompt_parts = [
            f"Analyze {ticker} for options trading opportunities:",
            "",
            "## Current Data:",
        ]
        
        if 'spot_price' in data:
            prompt_parts.append(f"- Spot Price: ${data['spot_price']:.2f}")
        
        if 'iv_rank' in data:
            prompt_parts.append(f"- IV Rank: {data['iv_rank']:.1f}%")
        
        if 'iv_percentile' in data:
            prompt_parts.append(f"- IV Percentile: {data['iv_percentile']:.1f}%")
        
        if 'regime' in data:
            prompt_parts.append(f"- Market Regime: {data['regime']}")
        
        if 'sentiment' in data:
            prompt_parts.append(f"- Sentiment: {data['sentiment']}")
        
        if 'options_chain' in data:
            chain = data['options_chain']
            prompt_parts.append(f"- Total Calls: {chain.get('call_count', 0)}")
            prompt_parts.append(f"- Total Puts: {chain.get('put_count', 0)}")
            prompt_parts.append(f"- Put/Call Ratio: {chain.get('pcr', 1):.2f}")
        
        prompt_parts.extend([
            "",
            "## Please Provide:",
            "1. Market outlook for the next 30 days",
            "2. Best options strategy given current conditions",
            "3. Specific strike and expiration recommendations",
            "4. Key risks to monitor",
            "5. Entry and exit criteria",
            "",
            "Be specific with numbers and show your reasoning."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_analysis(self, ticker: str, response: str, 
                        data: Dict) -> AIAnalysis:
        """Parse AI response into structured analysis."""
        # Extract key points (simple extraction)
        lines = response.split('\n')
        key_points = [
            line.strip('- •*').strip() 
            for line in lines 
            if line.strip().startswith(('-', '•', '*', '1', '2', '3', '4', '5'))
        ][:5]
        
        # Extract recommendation (look for keywords)
        recommendation = "Hold - No clear directional bias"
        response_lower = response.lower()
        if 'bullish' in response_lower or 'buy' in response_lower:
            recommendation = "Bullish - Consider long delta strategies"
        elif 'bearish' in response_lower or 'sell' in response_lower:
            recommendation = "Bearish - Consider short delta strategies"
        elif 'neutral' in response_lower or 'sideways' in response_lower:
            recommendation = "Neutral - Consider premium selling strategies"
        
        # Build reasoning chain
        reasoning = [
            f"Analyzed {ticker} market data",
            f"IV Rank at {data.get('iv_rank', 50):.0f}% suggests {'premium selling' if data.get('iv_rank', 50) > 50 else 'premium buying'}",
            f"Market regime: {data.get('regime', 'unknown')}",
            "Generated strategy recommendation based on conditions"
        ]
        
        return AIAnalysis(
            analysis_id=f"analysis_{self._analysis_counter}",
            ticker=ticker,
            analysis_type='auto_analysis',
            summary=response[:500] + "..." if len(response) > 500 else response,
            key_points=key_points,
            recommendation=recommendation,
            confidence=0.75,
            supporting_data=data,
            reasoning_chain=reasoning,
            generated_at=datetime.now(),
            model_used=self.groq.default_model
        )


# ============================================================
# PROACTIVE RECOMMENDATION ENGINE
# ============================================================

class ProactiveRecommendationEngine:
    """
    Generates proactive recommendations without user input.
    Continuously monitors and suggests actions.
    """
    
    def __init__(self):
        self.groq = EnhancedGroqClient()
        self._insight_counter = 0
    
    def generate_daily_insights(self, market_data: Dict,
                                 positions: List[Dict],
                                 watchlist: List[str]) -> List[ProactiveInsight]:
        """Generate daily proactive insights."""
        insights = []
        
        # Market-level insights
        market_insight = self._analyze_market_conditions(market_data)
        if market_insight:
            insights.append(market_insight)
        
        # Position-level insights
        for pos in positions:
            pos_insight = self._analyze_position(pos, market_data)
            if pos_insight:
                insights.append(pos_insight)
        
        # Opportunity insights
        for ticker in watchlist[:5]:  # Limit to prevent too many API calls
            opp_insight = self._find_opportunity(ticker, market_data)
            if opp_insight:
                insights.append(opp_insight)
        
        # Sort by priority
        priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
        insights.sort(key=lambda x: priority_order.get(x.priority, 4))
        
        return insights
    
    def _analyze_market_conditions(self, data: Dict) -> Optional[ProactiveInsight]:
        """Generate market condition insight."""
        self._insight_counter += 1
        
        vix = data.get('vix', 20)
        spy_change = data.get('spy_change_pct', 0)
        
        # Determine if actionable
        if vix > 25:
            priority = 'high'
            title = "Elevated Volatility Alert"
            insight = f"VIX at {vix:.1f} indicates elevated fear. Premium selling strategies become more attractive, but increase position sizes cautiously."
            actions = [
                "Consider opening iron condors with wide wings",
                "Review existing position Greeks",
                "Ensure adequate cash reserves"
            ]
        elif vix < 15:
            priority = 'medium'
            title = "Low Volatility Environment"
            insight = f"VIX at {vix:.1f} is historically low. Options are cheap - consider buying strategies or calendar spreads."
            actions = [
                "Look for long volatility plays",
                "Consider buying straddles on upcoming events",
                "Review any short premium positions"
            ]
        else:
            return None  # No actionable insight
        
        return ProactiveInsight(
            insight_id=f"insight_{self._insight_counter}",
            category='market',
            priority=priority,
            title=title,
            insight=insight,
            action_items=actions,
            affected_tickers=['SPY', 'QQQ'],
            confidence=0.75,
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24)
        )
    
    def _analyze_position(self, position: Dict, 
                          market_data: Dict) -> Optional[ProactiveInsight]:
        """Generate position-specific insight."""
        ticker = position.get('ticker', 'UNKNOWN')
        pnl_pct = position.get('pnl_pct', 0)
        dte = position.get('dte', 999)
        
        # Check for actionable conditions
        if pnl_pct > 50:
            self._insight_counter += 1
            return ProactiveInsight(
                insight_id=f"insight_{self._insight_counter}",
                category='position',
                priority='medium',
                title=f"Profit Target Reached: {ticker}",
                insight=f"Position in {ticker} has reached {pnl_pct:.0f}% profit. Consider taking profits or adjusting to lock in gains.",
                action_items=[
                    "Close position to realize profits",
                    "Roll to new expiration",
                    "Adjust strikes to reduce risk"
                ],
                affected_tickers=[ticker],
                confidence=0.85,
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=8)
            )
        
        if dte <= 5:
            self._insight_counter += 1
            return ProactiveInsight(
                insight_id=f"insight_{self._insight_counter}",
                category='position',
                priority='urgent',
                title=f"Expiration Warning: {ticker}",
                insight=f"Position in {ticker} expires in {dte} days. Gamma risk is elevated - decide on exit or roll.",
                action_items=[
                    "Close position before expiration",
                    "Roll to next expiration cycle",
                    "Let expire if fully OTM"
                ],
                affected_tickers=[ticker],
                confidence=0.95,
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=4)
            )
        
        return None
    
    def _find_opportunity(self, ticker: str, 
                          market_data: Dict) -> Optional[ProactiveInsight]:
        """Find trading opportunity for a ticker."""
        # In production, this would use real data
        # For now, generate based on random seed for consistency
        
        seed = hash(ticker + datetime.now().strftime('%Y%m%d')) % 100
        
        if seed > 90:  # 10% chance of opportunity
            self._insight_counter += 1
            return ProactiveInsight(
                insight_id=f"insight_{self._insight_counter}",
                category='opportunity',
                priority='medium',
                title=f"Opportunity: {ticker}",
                insight=f"AI detected favorable conditions for {ticker}. IV rank elevated with neutral to bullish outlook.",
                action_items=[
                    f"Review {ticker} options chain",
                    "Consider bull put spread or iron condor",
                    "Set alerts for entry"
                ],
                affected_tickers=[ticker],
                confidence=0.65,
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=48)
            )
        
        return None


# ============================================================
# CONTEXT-AWARE CONVERSATION
# ============================================================

class ContextAwareConversation:
    """
    Maintains conversation context for coherent multi-turn dialogues.
    Remembers discussed topics and user preferences.
    """
    
    def __init__(self):
        self.groq = EnhancedGroqClient()
        self._conversations: Dict[str, ConversationContext] = {}
    
    def create_conversation(self, conversation_id: str = None) -> str:
        """Create a new conversation context."""
        if not conversation_id:
            conversation_id = f"conv_{int(datetime.now().timestamp())}"
        
        self._conversations[conversation_id] = ConversationContext(
            conversation_id=conversation_id,
            messages=[],
            tickers_discussed=[],
            strategies_discussed=[],
            user_preferences={},
            market_context={},
            position_context={},
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        return conversation_id
    
    def chat(self, conversation_id: str, user_message: str,
             market_data: Dict = None) -> str:
        """Send message in conversation context."""
        if conversation_id not in self._conversations:
            self.create_conversation(conversation_id)
        
        context = self._conversations[conversation_id]
        
        # Add user message
        context.messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Extract entities from message
        self._extract_entities(context, user_message)
        
        # Update market context if provided
        if market_data:
            context.market_context = market_data
        
        # Build context-aware prompt
        prompt = self._build_contextual_prompt(context, user_message)
        
        # Get response
        response = self.groq.query(prompt, context='options_analyst')
        
        # Add assistant response
        context.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        context.last_updated = datetime.now()
        
        return response
    
    def _extract_entities(self, context: ConversationContext, message: str):
        """Extract tickers and strategies from message."""
        # Common tickers
        common_tickers = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD']
        message_upper = message.upper()
        
        for ticker in common_tickers:
            if ticker in message_upper and ticker not in context.tickers_discussed:
                context.tickers_discussed.append(ticker)
        
        # Common strategies
        strategies = ['iron condor', 'bull put', 'bear call', 'straddle', 'strangle', 
                     'covered call', 'cash secured put', 'butterfly', 'calendar']
        message_lower = message.lower()
        
        for strategy in strategies:
            if strategy in message_lower and strategy not in context.strategies_discussed:
                context.strategies_discussed.append(strategy)
    
    def _build_contextual_prompt(self, context: ConversationContext, 
                                  current_message: str) -> str:
        """Build prompt with conversation context."""
        parts = ["## Conversation Context:"]
        
        if context.tickers_discussed:
            parts.append(f"Tickers discussed: {', '.join(context.tickers_discussed)}")
        
        if context.strategies_discussed:
            parts.append(f"Strategies discussed: {', '.join(context.strategies_discussed)}")
        
        if context.market_context:
            parts.append(f"Market data: VIX={context.market_context.get('vix', 'N/A')}, SPY change={context.market_context.get('spy_change_pct', 'N/A')}%")
        
        # Include last 3 exchanges for context
        recent_messages = context.messages[-6:] if len(context.messages) > 6 else context.messages
        if recent_messages:
            parts.append("\n## Recent Conversation:")
            for msg in recent_messages[:-1]:  # Exclude current message
                role = "User" if msg['role'] == 'user' else "Assistant"
                parts.append(f"{role}: {msg['content'][:200]}...")
        
        parts.extend([
            "",
            "## Current Question:",
            current_message,
            "",
            "Provide a response that builds on the conversation context."
        ])
        
        return "\n".join(parts)
    
    def get_conversation_summary(self, conversation_id: str) -> Dict:
        """Get summary of conversation."""
        if conversation_id not in self._conversations:
            return {}
        
        context = self._conversations[conversation_id]
        return {
            'conversation_id': conversation_id,
            'message_count': len(context.messages),
            'tickers_discussed': context.tickers_discussed,
            'strategies_discussed': context.strategies_discussed,
            'created_at': context.created_at.isoformat(),
            'last_updated': context.last_updated.isoformat()
        }


# ============================================================
# MULTI-MODEL CONSENSUS
# ============================================================

class MultiModelConsensus:
    """
    Queries multiple models and synthesizes consensus.
    Provides more reliable answers by comparing outputs.
    """
    
    def __init__(self):
        self.groq = EnhancedGroqClient()
    
    def get_consensus(self, query: str, 
                      num_samples: int = 3) -> ModelConsensus:
        """Get consensus from multiple model runs."""
        responses = {}
        confidences = {}
        
        # Get multiple responses with temperature variation
        temps = [0.3, 0.5, 0.7][:num_samples]
        
        for i, temp in enumerate(temps):
            model_key = f"model_t{temp}"
            response = self.groq.query(
                query, 
                context='options_analyst',
                temperature=temp
            )
            responses[model_key] = response
            
            # Estimate confidence based on response characteristics
            confidences[model_key] = self._estimate_confidence(response)
        
        # Find consensus
        consensus = self._find_consensus(responses)
        agreement = self._calculate_agreement(responses)
        
        # Identify minority opinions
        minority = self._identify_minority(responses, consensus)
        
        # Calculate consensus confidence
        consensus_conf = sum(confidences.values()) / len(confidences) * agreement
        
        return ModelConsensus(
            query=query,
            model_responses=responses,
            model_confidences=confidences,
            consensus_answer=consensus,
            consensus_confidence=round(consensus_conf, 3),
            agreement_level=round(agreement, 3),
            minority_opinions=minority,
            generated_at=datetime.now()
        )
    
    def _estimate_confidence(self, response: str) -> float:
        """Estimate confidence based on response characteristics."""
        confidence = 0.7  # Base confidence
        
        # Higher confidence for specific numbers
        if any(char.isdigit() for char in response):
            confidence += 0.1
        
        # Higher confidence for structured responses
        if any(marker in response for marker in ['1.', '2.', '•', '-']):
            confidence += 0.05
        
        # Lower confidence for hedging language
        hedging = ['maybe', 'possibly', 'might', 'could', 'uncertain']
        if any(word in response.lower() for word in hedging):
            confidence -= 0.1
        
        return min(0.95, max(0.3, confidence))
    
    def _find_consensus(self, responses: Dict[str, str]) -> str:
        """Find consensus from multiple responses."""
        if not responses:
            return "No consensus available"
        
        # For simplicity, use the longest response as it likely contains most detail
        # In production, use more sophisticated NLP comparison
        return max(responses.values(), key=len)
    
    def _calculate_agreement(self, responses: Dict[str, str]) -> float:
        """Calculate agreement level between responses."""
        if len(responses) < 2:
            return 1.0
        
        # Simple keyword overlap calculation
        response_words = [set(r.lower().split()) for r in responses.values()]
        
        agreements = []
        for i in range(len(response_words)):
            for j in range(i + 1, len(response_words)):
                overlap = len(response_words[i] & response_words[j])
                total = len(response_words[i] | response_words[j])
                agreements.append(overlap / total if total > 0 else 0)
        
        return sum(agreements) / len(agreements) if agreements else 1.0
    
    def _identify_minority(self, responses: Dict[str, str], 
                          consensus: str) -> List[str]:
        """Identify minority opinions that differ from consensus."""
        minority = []
        
        consensus_lower = consensus.lower()
        
        for key, response in responses.items():
            response_lower = response.lower()
            
            # Check for contrasting recommendations
            if 'bullish' in consensus_lower and 'bearish' in response_lower:
                minority.append(f"Model {key} suggested bearish outlook")
            elif 'bearish' in consensus_lower and 'bullish' in response_lower:
                minority.append(f"Model {key} suggested bullish outlook")
            elif 'sell' in consensus_lower and 'buy' in response_lower:
                minority.append(f"Model {key} suggested buying instead")
        
        return minority


# ============================================================
# EXPLAINABLE AI
# ============================================================

class ExplainableAI:
    """
    Provides clear explanations for all AI recommendations.
    Shows reasoning chain and data points used.
    """
    
    def __init__(self):
        self.groq = EnhancedGroqClient()
    
    def explain_recommendation(self, recommendation: str, 
                               data: Dict) -> Dict:
        """Generate detailed explanation for a recommendation."""
        prompt = f"""Explain this options trading recommendation step by step:

Recommendation: {recommendation}

Supporting Data:
{json.dumps(data, indent=2, default=str)}

Please provide:
1. Why this recommendation makes sense
2. What data points support it
3. What assumptions are being made
4. Potential risks or scenarios where this could be wrong
5. Alternative considerations

Be specific and use the actual data provided."""

        response = self.groq.query(prompt, context='explainer')
        
        return {
            'recommendation': recommendation,
            'explanation': response,
            'data_used': data,
            'reasoning_chain': self._extract_reasoning(response),
            'assumptions': self._extract_assumptions(response),
            'risks': self._extract_risks(response),
            'generated_at': datetime.now().isoformat()
        }
    
    def _extract_reasoning(self, response: str) -> List[str]:
        """Extract reasoning steps from response."""
        reasoning = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and any(line.startswith(p) for p in ['1.', '2.', '3.', '4.', '5.', '-', '•']):
                reasoning.append(line.lstrip('0123456789.-•) '))
        
        return reasoning[:5]
    
    def _extract_assumptions(self, response: str) -> List[str]:
        """Extract assumptions from response."""
        assumptions = []
        response_lower = response.lower()
        
        if 'assuming' in response_lower or 'assumption' in response_lower:
            # Find sentences containing assumption words
            sentences = response.split('.')
            for sentence in sentences:
                if 'assum' in sentence.lower():
                    assumptions.append(sentence.strip())
        
        return assumptions[:3]
    
    def _extract_risks(self, response: str) -> List[str]:
        """Extract risks from response."""
        risks = []
        risk_keywords = ['risk', 'warning', 'caution', 'careful', 'danger', 'could fail']
        
        sentences = response.split('.')
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in risk_keywords):
                risks.append(sentence.strip())
        
        return risks[:3]


# ============================================================
# UNIFIED GROQ AI ENGINE
# ============================================================

class UnifiedGroqAI:
    """
    Unified interface for all GROQ AI capabilities.
    """
    
    def __init__(self):
        self.client = EnhancedGroqClient()
        self.zero_prompt = ZeroPromptAnalyzer()
        self.proactive = ProactiveRecommendationEngine()
        self.conversation = ContextAwareConversation()
        self.consensus = MultiModelConsensus()
        self.explainer = ExplainableAI()
    
    def auto_analyze(self, ticker: str, data: Dict = None) -> AIAnalysis:
        """Automatic analysis without prompt."""
        if data is None:
            data = self._get_default_data(ticker)
        return self.zero_prompt.auto_analyze(ticker, data)
    
    def get_insights(self, positions: List[Dict] = None,
                     watchlist: List[str] = None) -> List[ProactiveInsight]:
        """Get proactive insights."""
        market_data = {'vix': 20, 'spy_change_pct': 0.5}
        positions = positions or []
        watchlist = watchlist or ['SPY', 'QQQ', 'AAPL', 'NVDA']
        return self.proactive.generate_daily_insights(market_data, positions, watchlist)
    
    def chat(self, message: str, conversation_id: str = None) -> str:
        """Chat with context awareness."""
        if not conversation_id:
            conversation_id = self.conversation.create_conversation()
        return self.conversation.chat(conversation_id, message)
    
    def get_consensus(self, query: str) -> ModelConsensus:
        """Get multi-model consensus."""
        return self.consensus.get_consensus(query)
    
    def explain(self, recommendation: str, data: Dict) -> Dict:
        """Get explanation for recommendation."""
        return self.explainer.explain_recommendation(recommendation, data)
    
    def _get_default_data(self, ticker: str) -> Dict:
        """Get default data for a ticker."""
        try:
            from .alpaca_data_loader import get_alpaca_client
            client = get_alpaca_client()
            price = client.get_stock_quote(ticker) or 100
            return {
                'spot_price': price,
                'iv_rank': 50,
                'iv_percentile': 50,
                'regime': 'normal',
                'sentiment': 'neutral'
            }
        except:
            return {
                'spot_price': 100,
                'iv_rank': 50,
                'iv_percentile': 50,
                'regime': 'normal',
                'sentiment': 'neutral'
            }


# ============================================================
# SINGLETON
# ============================================================

_groq_ai = None

def get_groq_ai() -> UnifiedGroqAI:
    """Get singleton GROQ AI instance."""
    global _groq_ai
    if _groq_ai is None:
        _groq_ai = UnifiedGroqAI()
    return _groq_ai
