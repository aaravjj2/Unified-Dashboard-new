"""
One-Click Trade Setup Module
============================
AI prepares complete trade setups with minimal user interaction.
Single click to get fully configured trade ready for execution.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class OptionLeg:
    """Single option leg in a trade."""
    action: str  # 'BUY' or 'SELL'
    option_type: str  # 'CALL' or 'PUT'
    strike: float
    expiration: str
    contracts: int
    premium: float
    delta: float = 0.0
    iv: float = 0.0


@dataclass
class TradeSetup:
    """Complete trade setup ready for execution."""
    setup_id: str
    ticker: str
    strategy_name: str
    legs: List[OptionLeg]
    
    # Position metrics
    total_cost: float  # Negative for credit, positive for debit
    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    probability_of_profit: float
    
    # Risk metrics
    risk_reward_ratio: float
    delta_exposure: float
    theta_per_day: float
    vega_exposure: float
    
    # Trade details
    days_to_expiry: int
    iv_rank: float
    underlying_price: float
    
    # AI insights
    rationale: str
    entry_criteria_met: bool
    exit_targets: Dict[str, float]  # {'profit': X, 'loss': Y, 'time': Z}
    
    # Execution
    order_type: str  # 'LIMIT', 'MARKET'
    limit_price: Optional[float]
    created_at: datetime


class OneClickTrader:
    """
    AI-powered trade setup generator.
    Creates complete, executable trade setups with one click.
    """
    
    def __init__(self):
        self._setup_counter = 0
        
        # Default risk parameters
        self.default_risk = {
            'max_position_size': 0.05,  # 5% of portfolio per trade
            'max_loss_per_trade': 0.02,  # 2% max loss per trade
            'profit_target_pct': 50,     # Take profit at 50% of max
            'stop_loss_pct': 200,        # Stop at 2x credit received
            'preferred_dte': 45,         # Default days to expiry
            'min_pop': 60,               # Minimum probability of profit
        }
    
    def generate_trade_setup(self, ticker: str, strategy: str = 'auto',
                            account_size: float = 10000,
                            risk_level: str = 'moderate') -> Optional[TradeSetup]:
        """
        Generate a complete trade setup for a ticker.
        
        Args:
            ticker: Stock symbol
            strategy: Strategy name or 'auto' for AI selection
            account_size: Total account size for position sizing
            risk_level: 'conservative', 'moderate', or 'aggressive'
        
        Returns:
            Complete TradeSetup ready for execution
        """
        try:
            from .alpaca_data_loader import fetch_options_chain_alpaca_only
            from .ai_ml_engine import get_ai_selector
            from .sentiment_analyzer import get_sentiment_analyzer
            
            # Get market data
            chain = fetch_options_chain_alpaca_only(ticker)
            if chain.get('error') or not chain.get('spot_price'):
                logger.warning(f"Could not get data for {ticker}")
                return None
            
            spot_price = chain['spot_price']
            calls_df = chain.get('calls', [])
            puts_df = chain.get('puts', [])
            expirations = chain.get('expirations', [])
            
            if len(calls_df) == 0 or len(puts_df) == 0:
                logger.warning(f"Insufficient options data for {ticker}")
                return None
            
            # Convert DataFrame to list if needed
            if hasattr(calls_df, 'to_dict'):
                calls = calls_df.to_dict('records')
                puts = puts_df.to_dict('records')
            else:
                calls = calls_df
                puts = puts_df
            
            # Determine strategy
            if strategy == 'auto':
                selector = get_ai_selector()
                strategy_rec = selector.get_best_strategy(ticker)
                if strategy_rec:
                    strategy = strategy_rec.strategy_name
                else:
                    strategy = 'Iron Condor'  # Default
            
            # Adjust risk parameters based on risk level
            risk_params = self._get_risk_params(risk_level)
            
            # Generate setup based on strategy
            if strategy.lower() in ['iron condor', 'iron_condor']:
                return self._setup_iron_condor(ticker, spot_price, calls, puts, expirations, 
                                              account_size, risk_params)
            
            elif strategy.lower() in ['bull put spread', 'bull_put_spread', 'put spread']:
                return self._setup_bull_put_spread(ticker, spot_price, puts, expirations,
                                                   account_size, risk_params)
            
            elif strategy.lower() in ['bear call spread', 'bear_call_spread', 'call spread']:
                return self._setup_bear_call_spread(ticker, spot_price, calls, expirations,
                                                    account_size, risk_params)
            
            elif strategy.lower() in ['covered call', 'covered_call']:
                return self._setup_covered_call(ticker, spot_price, calls, expirations,
                                               account_size, risk_params)
            
            elif strategy.lower() in ['cash secured put', 'cash_secured_put', 'csp']:
                return self._setup_cash_secured_put(ticker, spot_price, puts, expirations,
                                                    account_size, risk_params)
            
            elif strategy.lower() in ['long straddle', 'straddle']:
                return self._setup_straddle(ticker, spot_price, calls, puts, expirations,
                                           account_size, risk_params)
            
            else:
                # Default to iron condor for undefined strategies
                return self._setup_iron_condor(ticker, spot_price, calls, puts, expirations,
                                              account_size, risk_params)
            
        except Exception as e:
            logger.error(f"Trade setup error for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_risk_params(self, risk_level: str) -> Dict:
        """Get risk parameters based on risk level."""
        params = self.default_risk.copy()
        
        if risk_level == 'conservative':
            params['max_position_size'] = 0.03
            params['max_loss_per_trade'] = 0.01
            params['min_pop'] = 70
            params['preferred_dte'] = 60
        elif risk_level == 'aggressive':
            params['max_position_size'] = 0.08
            params['max_loss_per_trade'] = 0.03
            params['min_pop'] = 50
            params['preferred_dte'] = 30
        
        return params
    
    def _find_optimal_expiration(self, expirations: List[str], target_dte: int) -> str:
        """Find expiration closest to target DTE."""
        if not expirations:
            return (datetime.now() + timedelta(days=target_dte)).strftime('%Y-%m-%d')
        
        today = datetime.now()
        best_exp = expirations[0]
        best_diff = float('inf')
        
        for exp in expirations:
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                dte = (exp_date - today).days
                diff = abs(dte - target_dte)
                
                if diff < best_diff and dte > 0:
                    best_diff = diff
                    best_exp = exp
            except:
                continue
        
        return best_exp
    
    def _find_strike_by_delta(self, options: List[Dict], target_delta: float, 
                             option_type: str) -> Optional[Dict]:
        """Find option with delta closest to target."""
        best_option = None
        best_diff = float('inf')
        
        for opt in options:
            delta = abs(opt.get('delta', 0.5))
            if option_type == 'PUT':
                delta = -delta  # Puts have negative delta
            
            diff = abs(delta - target_delta)
            if diff < best_diff:
                best_diff = diff
                best_option = opt
        
        return best_option
    
    def _find_strike_by_distance(self, options: List[Dict], spot: float, 
                                 distance_pct: float, direction: str) -> Optional[Dict]:
        """Find option at specific distance from spot."""
        if direction == 'above':
            target = spot * (1 + distance_pct / 100)
        else:
            target = spot * (1 - distance_pct / 100)
        
        best_option = None
        best_diff = float('inf')
        
        for opt in options:
            strike = opt.get('strike', 0)
            diff = abs(strike - target)
            
            if diff < best_diff:
                best_diff = diff
                best_option = opt
        
        return best_option
    
    def _create_setup_id(self) -> str:
        """Generate unique setup ID."""
        self._setup_counter += 1
        return f"setup_{self._setup_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _setup_iron_condor(self, ticker: str, spot: float, calls: List[Dict],
                          puts: List[Dict], expirations: List[str],
                          account_size: float, risk_params: Dict) -> Optional[TradeSetup]:
        """Generate iron condor setup."""
        try:
            # Find optimal expiration
            exp = self._find_optimal_expiration(expirations, risk_params['preferred_dte'])
            
            # Filter options by expiration
            exp_calls = [c for c in calls if c.get('expiration') == exp]
            exp_puts = [p for p in puts if p.get('expiration') == exp]
            
            if not exp_calls or not exp_puts:
                # Use all options if filtering fails
                exp_calls = calls
                exp_puts = puts
            
            # Find strikes: sell ~0.30 delta, buy ~0.15 delta
            # For iron condor: sell call spread above, sell put spread below
            
            # Call spread (bear call spread component)
            sell_call = self._find_strike_by_distance(exp_calls, spot, 5, 'above')
            buy_call = self._find_strike_by_distance(exp_calls, spot, 8, 'above')
            
            # Put spread (bull put spread component)
            sell_put = self._find_strike_by_distance(exp_puts, spot, 5, 'below')
            buy_put = self._find_strike_by_distance(exp_puts, spot, 8, 'below')
            
            if not all([sell_call, buy_call, sell_put, buy_put]):
                logger.warning(f"Could not find all strikes for iron condor on {ticker}")
                return None
            
            # Calculate position size based on risk
            call_spread_width = buy_call['strike'] - sell_call['strike']
            put_spread_width = sell_put['strike'] - buy_put['strike']
            max_width = max(call_spread_width, put_spread_width)
            
            # Credit received
            sell_call_mid = (sell_call.get('bid', 0) + sell_call.get('ask', 0)) / 2
            buy_call_mid = (buy_call.get('bid', 0) + buy_call.get('ask', 0)) / 2
            sell_put_mid = (sell_put.get('bid', 0) + sell_put.get('ask', 0)) / 2
            buy_put_mid = (buy_put.get('bid', 0) + buy_put.get('ask', 0)) / 2
            
            credit = (sell_call_mid - buy_call_mid) + (sell_put_mid - buy_put_mid)
            max_loss_per_contract = (max_width - credit) * 100
            
            # Position sizing
            max_risk = account_size * risk_params['max_loss_per_trade']
            contracts = max(1, int(max_risk / max_loss_per_contract))
            
            # Build legs
            legs = [
                OptionLeg(
                    action='SELL', option_type='CALL',
                    strike=sell_call['strike'], expiration=exp,
                    contracts=contracts, premium=sell_call_mid,
                    delta=sell_call.get('delta', 0.3),
                    iv=sell_call.get('impliedVolatility', 0.3)
                ),
                OptionLeg(
                    action='BUY', option_type='CALL',
                    strike=buy_call['strike'], expiration=exp,
                    contracts=contracts, premium=buy_call_mid,
                    delta=buy_call.get('delta', 0.15),
                    iv=buy_call.get('impliedVolatility', 0.35)
                ),
                OptionLeg(
                    action='SELL', option_type='PUT',
                    strike=sell_put['strike'], expiration=exp,
                    contracts=contracts, premium=sell_put_mid,
                    delta=sell_put.get('delta', -0.3),
                    iv=sell_put.get('impliedVolatility', 0.3)
                ),
                OptionLeg(
                    action='BUY', option_type='PUT',
                    strike=buy_put['strike'], expiration=exp,
                    contracts=contracts, premium=buy_put_mid,
                    delta=buy_put.get('delta', -0.15),
                    iv=buy_put.get('impliedVolatility', 0.35)
                )
            ]
            
            # Calculate metrics
            total_credit = credit * contracts * 100
            max_profit = total_credit
            max_loss = (max_width - credit) * contracts * 100
            
            # Breakevens
            lower_be = sell_put['strike'] - credit
            upper_be = sell_call['strike'] + credit
            
            # Calculate DTE
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                dte = (exp_date - datetime.now()).days
            except:
                dte = risk_params['preferred_dte']
            
            # Calculate Greeks
            net_delta = sum(l.delta * l.contracts * (1 if l.action == 'BUY' else -1) for l in legs)
            
            # Estimate theta (rough)
            theta_per_day = total_credit / dte if dte > 0 else 0
            
            # POP estimate
            range_size = (upper_be - lower_be) / spot
            pop = min(0.85, 0.5 + range_size)  # Rough estimate
            
            return TradeSetup(
                setup_id=self._create_setup_id(),
                ticker=ticker,
                strategy_name='Iron Condor',
                legs=legs,
                total_cost=-total_credit,  # Credit = negative cost
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=[round(lower_be, 2), round(upper_be, 2)],
                probability_of_profit=pop,
                risk_reward_ratio=round(max_profit / max_loss, 2) if max_loss > 0 else 0,
                delta_exposure=round(net_delta, 2),
                theta_per_day=round(theta_per_day, 2),
                vega_exposure=0,  # Would need proper calculation
                days_to_expiry=dte,
                iv_rank=50,  # Would need to calculate
                underlying_price=spot,
                rationale=f"Iron condor on {ticker}: Collect ${total_credit:.0f} credit with defined risk. Profit if {ticker} stays between ${lower_be:.0f} and ${upper_be:.0f}.",
                entry_criteria_met=True,
                exit_targets={
                    'profit_target': total_credit * risk_params['profit_target_pct'] / 100,
                    'stop_loss': -total_credit * risk_params['stop_loss_pct'] / 100,
                    'days_before_exp': min(7, dte // 3)
                },
                order_type='LIMIT',
                limit_price=round(credit, 2),
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Iron condor setup error: {e}")
            return None
    
    def _setup_bull_put_spread(self, ticker: str, spot: float, puts: List[Dict],
                              expirations: List[str], account_size: float,
                              risk_params: Dict) -> Optional[TradeSetup]:
        """Generate bull put spread setup."""
        try:
            exp = self._find_optimal_expiration(expirations, risk_params['preferred_dte'])
            exp_puts = [p for p in puts if p.get('expiration') == exp] or puts
            
            # Find strikes
            sell_put = self._find_strike_by_distance(exp_puts, spot, 5, 'below')
            buy_put = self._find_strike_by_distance(exp_puts, spot, 10, 'below')
            
            if not sell_put or not buy_put:
                return None
            
            width = sell_put['strike'] - buy_put['strike']
            sell_mid = (sell_put.get('bid', 0) + sell_put.get('ask', 0)) / 2
            buy_mid = (buy_put.get('bid', 0) + buy_put.get('ask', 0)) / 2
            credit = sell_mid - buy_mid
            
            max_loss_per = (width - credit) * 100
            max_risk = account_size * risk_params['max_loss_per_trade']
            contracts = max(1, int(max_risk / max_loss_per))
            
            legs = [
                OptionLeg('SELL', 'PUT', sell_put['strike'], exp, contracts, sell_mid,
                         sell_put.get('delta', -0.3), sell_put.get('impliedVolatility', 0.3)),
                OptionLeg('BUY', 'PUT', buy_put['strike'], exp, contracts, buy_mid,
                         buy_put.get('delta', -0.15), buy_put.get('impliedVolatility', 0.35))
            ]
            
            total_credit = credit * contracts * 100
            max_loss = (width - credit) * contracts * 100
            breakeven = sell_put['strike'] - credit
            
            try:
                dte = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
            except:
                dte = risk_params['preferred_dte']
            
            return TradeSetup(
                setup_id=self._create_setup_id(),
                ticker=ticker,
                strategy_name='Bull Put Spread',
                legs=legs,
                total_cost=-total_credit,
                max_profit=total_credit,
                max_loss=max_loss,
                breakeven_points=[round(breakeven, 2)],
                probability_of_profit=0.65,
                risk_reward_ratio=round(total_credit / max_loss, 2) if max_loss > 0 else 0,
                delta_exposure=round(legs[0].delta * contracts + legs[1].delta * contracts, 2),
                theta_per_day=round(total_credit / dte, 2) if dte > 0 else 0,
                vega_exposure=0,
                days_to_expiry=dte,
                iv_rank=50,
                underlying_price=spot,
                rationale=f"Bull put spread on {ticker}: Bullish bias with ${total_credit:.0f} credit. Profit if {ticker} stays above ${breakeven:.0f}.",
                entry_criteria_met=True,
                exit_targets={
                    'profit_target': total_credit * 0.5,
                    'stop_loss': -total_credit * 2,
                    'days_before_exp': 7
                },
                order_type='LIMIT',
                limit_price=round(credit, 2),
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Bull put spread setup error: {e}")
            return None
    
    def _setup_bear_call_spread(self, ticker: str, spot: float, calls: List[Dict],
                               expirations: List[str], account_size: float,
                               risk_params: Dict) -> Optional[TradeSetup]:
        """Generate bear call spread setup."""
        try:
            exp = self._find_optimal_expiration(expirations, risk_params['preferred_dte'])
            exp_calls = [c for c in calls if c.get('expiration') == exp] or calls
            
            sell_call = self._find_strike_by_distance(exp_calls, spot, 5, 'above')
            buy_call = self._find_strike_by_distance(exp_calls, spot, 10, 'above')
            
            if not sell_call or not buy_call:
                return None
            
            width = buy_call['strike'] - sell_call['strike']
            sell_mid = (sell_call.get('bid', 0) + sell_call.get('ask', 0)) / 2
            buy_mid = (buy_call.get('bid', 0) + buy_call.get('ask', 0)) / 2
            credit = sell_mid - buy_mid
            
            max_loss_per = (width - credit) * 100
            max_risk = account_size * risk_params['max_loss_per_trade']
            contracts = max(1, int(max_risk / max_loss_per))
            
            legs = [
                OptionLeg('SELL', 'CALL', sell_call['strike'], exp, contracts, sell_mid,
                         sell_call.get('delta', 0.3), sell_call.get('impliedVolatility', 0.3)),
                OptionLeg('BUY', 'CALL', buy_call['strike'], exp, contracts, buy_mid,
                         buy_call.get('delta', 0.15), buy_call.get('impliedVolatility', 0.35))
            ]
            
            total_credit = credit * contracts * 100
            max_loss = (width - credit) * contracts * 100
            breakeven = sell_call['strike'] + credit
            
            try:
                dte = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
            except:
                dte = risk_params['preferred_dte']
            
            return TradeSetup(
                setup_id=self._create_setup_id(),
                ticker=ticker,
                strategy_name='Bear Call Spread',
                legs=legs,
                total_cost=-total_credit,
                max_profit=total_credit,
                max_loss=max_loss,
                breakeven_points=[round(breakeven, 2)],
                probability_of_profit=0.65,
                risk_reward_ratio=round(total_credit / max_loss, 2) if max_loss > 0 else 0,
                delta_exposure=round(-legs[0].delta * contracts - legs[1].delta * contracts, 2),
                theta_per_day=round(total_credit / dte, 2) if dte > 0 else 0,
                vega_exposure=0,
                days_to_expiry=dte,
                iv_rank=50,
                underlying_price=spot,
                rationale=f"Bear call spread on {ticker}: Bearish bias with ${total_credit:.0f} credit. Profit if {ticker} stays below ${breakeven:.0f}.",
                entry_criteria_met=True,
                exit_targets={
                    'profit_target': total_credit * 0.5,
                    'stop_loss': -total_credit * 2,
                    'days_before_exp': 7
                },
                order_type='LIMIT',
                limit_price=round(credit, 2),
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Bear call spread setup error: {e}")
            return None
    
    def _setup_covered_call(self, ticker: str, spot: float, calls: List[Dict],
                           expirations: List[str], account_size: float,
                           risk_params: Dict) -> Optional[TradeSetup]:
        """Generate covered call setup."""
        try:
            exp = self._find_optimal_expiration(expirations, 30)  # Shorter DTE for covered calls
            exp_calls = [c for c in calls if c.get('expiration') == exp] or calls
            
            # Find ~0.30 delta call
            sell_call = self._find_strike_by_distance(exp_calls, spot, 3, 'above')
            
            if not sell_call:
                return None
            
            call_mid = (sell_call.get('bid', 0) + sell_call.get('ask', 0)) / 2
            
            # 100 shares per contract
            stock_cost = spot * 100
            contracts = max(1, int(account_size * risk_params['max_position_size'] / stock_cost))
            
            legs = [
                OptionLeg('BUY', 'STOCK', spot, '', contracts * 100, spot, 1.0, 0),  # Stock
                OptionLeg('SELL', 'CALL', sell_call['strike'], exp, contracts, call_mid,
                         sell_call.get('delta', 0.3), sell_call.get('impliedVolatility', 0.25))
            ]
            
            premium = call_mid * contracts * 100
            max_profit = (sell_call['strike'] - spot) * contracts * 100 + premium
            max_loss = spot * contracts * 100 - premium  # If stock goes to 0
            
            try:
                dte = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
            except:
                dte = 30
            
            return TradeSetup(
                setup_id=self._create_setup_id(),
                ticker=ticker,
                strategy_name='Covered Call',
                legs=legs,
                total_cost=stock_cost * contracts - premium,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=[round(spot - call_mid, 2)],
                probability_of_profit=0.75,
                risk_reward_ratio=round(max_profit / (stock_cost - premium), 2),
                delta_exposure=round(contracts * 100 - sell_call.get('delta', 0.3) * contracts * 100, 0),
                theta_per_day=round(premium / dte, 2) if dte > 0 else 0,
                vega_exposure=0,
                days_to_expiry=dte,
                iv_rank=50,
                underlying_price=spot,
                rationale=f"Covered call on {ticker}: Own {contracts * 100} shares and sell calls for ${premium:.0f} premium. Called away at ${sell_call['strike']:.0f}.",
                entry_criteria_met=True,
                exit_targets={
                    'profit_target': max_profit * 0.5,
                    'stop_loss': -stock_cost * 0.08,  # 8% stock drop
                    'days_before_exp': 5
                },
                order_type='LIMIT',
                limit_price=round(call_mid, 2),
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Covered call setup error: {e}")
            return None
    
    def _setup_cash_secured_put(self, ticker: str, spot: float, puts: List[Dict],
                               expirations: List[str], account_size: float,
                               risk_params: Dict) -> Optional[TradeSetup]:
        """Generate cash secured put setup."""
        try:
            exp = self._find_optimal_expiration(expirations, 30)
            exp_puts = [p for p in puts if p.get('expiration') == exp] or puts
            
            sell_put = self._find_strike_by_distance(exp_puts, spot, 5, 'below')
            
            if not sell_put:
                return None
            
            put_mid = (sell_put.get('bid', 0) + sell_put.get('ask', 0)) / 2
            
            # Cash needed per contract
            cash_per = sell_put['strike'] * 100
            contracts = max(1, int(account_size * risk_params['max_position_size'] / cash_per))
            
            legs = [
                OptionLeg('SELL', 'PUT', sell_put['strike'], exp, contracts, put_mid,
                         sell_put.get('delta', -0.3), sell_put.get('impliedVolatility', 0.25))
            ]
            
            premium = put_mid * contracts * 100
            max_profit = premium
            max_loss = (sell_put['strike'] - put_mid) * contracts * 100  # If stock goes to 0
            
            try:
                dte = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
            except:
                dte = 30
            
            return TradeSetup(
                setup_id=self._create_setup_id(),
                ticker=ticker,
                strategy_name='Cash Secured Put',
                legs=legs,
                total_cost=-premium,
                max_profit=premium,
                max_loss=max_loss,
                breakeven_points=[round(sell_put['strike'] - put_mid, 2)],
                probability_of_profit=0.70,
                risk_reward_ratio=round(premium / max_loss, 2) if max_loss > 0 else 0,
                delta_exposure=round(-sell_put.get('delta', -0.3) * contracts * 100, 0),
                theta_per_day=round(premium / dte, 2) if dte > 0 else 0,
                vega_exposure=0,
                days_to_expiry=dte,
                iv_rank=50,
                underlying_price=spot,
                rationale=f"Cash secured put on {ticker}: Collect ${premium:.0f} to buy {contracts * 100} shares at ${sell_put['strike']:.0f} if assigned.",
                entry_criteria_met=True,
                exit_targets={
                    'profit_target': premium * 0.5,
                    'stop_loss': -premium * 2,
                    'days_before_exp': 5
                },
                order_type='LIMIT',
                limit_price=round(put_mid, 2),
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"CSP setup error: {e}")
            return None
    
    def _setup_straddle(self, ticker: str, spot: float, calls: List[Dict],
                       puts: List[Dict], expirations: List[str],
                       account_size: float, risk_params: Dict) -> Optional[TradeSetup]:
        """Generate long straddle setup."""
        try:
            exp = self._find_optimal_expiration(expirations, risk_params['preferred_dte'])
            
            # Find ATM options
            atm_call = min(calls, key=lambda x: abs(x.get('strike', 0) - spot))
            atm_put = min(puts, key=lambda x: abs(x.get('strike', 0) - spot))
            
            if not atm_call or not atm_put:
                return None
            
            call_mid = (atm_call.get('bid', 0) + atm_call.get('ask', 0)) / 2
            put_mid = (atm_put.get('bid', 0) + atm_put.get('ask', 0)) / 2
            total_premium = call_mid + put_mid
            
            max_cost = account_size * risk_params['max_loss_per_trade']
            contracts = max(1, int(max_cost / (total_premium * 100)))
            
            legs = [
                OptionLeg('BUY', 'CALL', atm_call['strike'], exp, contracts, call_mid,
                         atm_call.get('delta', 0.5), atm_call.get('impliedVolatility', 0.25)),
                OptionLeg('BUY', 'PUT', atm_put['strike'], exp, contracts, put_mid,
                         atm_put.get('delta', -0.5), atm_put.get('impliedVolatility', 0.25))
            ]
            
            cost = total_premium * contracts * 100
            
            try:
                dte = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
            except:
                dte = risk_params['preferred_dte']
            
            return TradeSetup(
                setup_id=self._create_setup_id(),
                ticker=ticker,
                strategy_name='Long Straddle',
                legs=legs,
                total_cost=cost,
                max_profit=float('inf'),  # Unlimited
                max_loss=cost,
                breakeven_points=[
                    round(atm_call['strike'] - total_premium, 2),
                    round(atm_call['strike'] + total_premium, 2)
                ],
                probability_of_profit=0.35,  # Straddles have lower POP
                risk_reward_ratio=2.0,  # Potential for big moves
                delta_exposure=0,  # Delta neutral at entry
                theta_per_day=-round(cost / dte, 2) if dte > 0 else 0,  # Negative theta
                vega_exposure=round(contracts * 100, 0),  # Long vega
                days_to_expiry=dte,
                iv_rank=50,
                underlying_price=spot,
                rationale=f"Long straddle on {ticker}: Bet on big move in either direction. Breakevens at ${atm_call['strike'] - total_premium:.0f} and ${atm_call['strike'] + total_premium:.0f}.",
                entry_criteria_met=True,
                exit_targets={
                    'profit_target': cost * 1.5,  # 150% return
                    'stop_loss': -cost * 0.5,  # 50% of premium
                    'days_before_exp': 14
                },
                order_type='LIMIT',
                limit_price=round(total_premium, 2),
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Straddle setup error: {e}")
            return None


# Singleton
_one_click_trader = None

def get_one_click_trader() -> OneClickTrader:
    """Get singleton trader."""
    global _one_click_trader
    if _one_click_trader is None:
        _one_click_trader = OneClickTrader()
    return _one_click_trader


def generate_quick_trade(ticker: str, strategy: str = 'auto',
                        account_size: float = 10000,
                        risk_level: str = 'moderate') -> Optional[Dict]:
    """
    Generate a quick trade setup for UI.
    """
    trader = get_one_click_trader()
    setup = trader.generate_trade_setup(ticker, strategy, account_size, risk_level)
    
    if not setup:
        return None
    
    return {
        'id': setup.setup_id,
        'ticker': setup.ticker,
        'strategy': setup.strategy_name,
        'legs': [
            {
                'action': leg.action,
                'type': leg.option_type,
                'strike': leg.strike,
                'expiration': leg.expiration,
                'contracts': leg.contracts,
                'premium': round(leg.premium, 2)
            }
            for leg in setup.legs
        ],
        'metrics': {
            'total_cost': round(setup.total_cost, 0),
            'max_profit': round(setup.max_profit, 0) if setup.max_profit != float('inf') else 'Unlimited',
            'max_loss': round(setup.max_loss, 0),
            'breakevens': setup.breakeven_points,
            'pop': round(setup.probability_of_profit * 100, 0),
            'risk_reward': setup.risk_reward_ratio
        },
        'greeks': {
            'delta': setup.delta_exposure,
            'theta': setup.theta_per_day,
            'vega': setup.vega_exposure
        },
        'details': {
            'dte': setup.days_to_expiry,
            'underlying': setup.underlying_price,
            'rationale': setup.rationale
        },
        'order': {
            'type': setup.order_type,
            'limit': setup.limit_price
        },
        'exit_targets': setup.exit_targets,
        'created_at': setup.created_at.isoformat()
    }
