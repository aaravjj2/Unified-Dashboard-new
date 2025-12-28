"""
Fundamental Features - Feature Engineering for Fundamental Data
================================================================
Phase 1 of ML Project Guide implementation.

Pure, unit-testable functions for computing fundamental features.
"""

import logging
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ==============================================================================
# VALUATION RATIOS
# ==============================================================================

def compute_pe_ratio(price: float, eps: float) -> float:
    """
    Compute Price-to-Earnings ratio.
    
    Args:
        price: Stock price
        eps: Earnings per share
        
    Returns:
        P/E ratio
    """
    if eps == 0 or pd.isna(eps):
        return np.nan
    return price / eps


def compute_pb_ratio(price: float, book_value_per_share: float) -> float:
    """Compute Price-to-Book ratio."""
    if book_value_per_share <= 0 or pd.isna(book_value_per_share):
        return np.nan
    return price / book_value_per_share


def compute_ps_ratio(market_cap: float, revenue: float) -> float:
    """Compute Price-to-Sales ratio."""
    if revenue <= 0 or pd.isna(revenue):
        return np.nan
    return market_cap / revenue


def compute_peg_ratio(pe_ratio: float, earnings_growth: float) -> float:
    """Compute PEG ratio (P/E to Growth)."""
    if earnings_growth <= 0 or pd.isna(earnings_growth):
        return np.nan
    return pe_ratio / (earnings_growth * 100)  # earnings_growth should be decimal


def compute_ev_ebitda(enterprise_value: float, ebitda: float) -> float:
    """Compute EV/EBITDA ratio."""
    if ebitda <= 0 or pd.isna(ebitda):
        return np.nan
    return enterprise_value / ebitda


def compute_ev_revenue(enterprise_value: float, revenue: float) -> float:
    """Compute EV/Revenue ratio."""
    if revenue <= 0 or pd.isna(revenue):
        return np.nan
    return enterprise_value / revenue


def compute_dividend_yield(dividend_per_share: float, price: float) -> float:
    """Compute dividend yield."""
    if price <= 0 or pd.isna(price):
        return np.nan
    return (dividend_per_share / price) * 100


# ==============================================================================
# PROFITABILITY RATIOS
# ==============================================================================

def compute_gross_margin(gross_profit: float, revenue: float) -> float:
    """Compute gross margin."""
    if revenue <= 0 or pd.isna(revenue):
        return np.nan
    return gross_profit / revenue


def compute_operating_margin(operating_income: float, revenue: float) -> float:
    """Compute operating margin."""
    if revenue <= 0 or pd.isna(revenue):
        return np.nan
    return operating_income / revenue


def compute_net_margin(net_income: float, revenue: float) -> float:
    """Compute net profit margin."""
    if revenue <= 0 or pd.isna(revenue):
        return np.nan
    return net_income / revenue


def compute_roe(net_income: float, shareholders_equity: float) -> float:
    """Compute Return on Equity."""
    if shareholders_equity <= 0 or pd.isna(shareholders_equity):
        return np.nan
    return net_income / shareholders_equity


def compute_roa(net_income: float, total_assets: float) -> float:
    """Compute Return on Assets."""
    if total_assets <= 0 or pd.isna(total_assets):
        return np.nan
    return net_income / total_assets


def compute_roic(
    operating_income: float,
    tax_rate: float,
    invested_capital: float
) -> float:
    """Compute Return on Invested Capital."""
    if invested_capital <= 0 or pd.isna(invested_capital):
        return np.nan
    nopat = operating_income * (1 - tax_rate)
    return nopat / invested_capital


# ==============================================================================
# LEVERAGE & SOLVENCY RATIOS
# ==============================================================================

def compute_debt_to_equity(total_debt: float, shareholders_equity: float) -> float:
    """Compute Debt-to-Equity ratio."""
    if shareholders_equity <= 0 or pd.isna(shareholders_equity):
        return np.nan
    return total_debt / shareholders_equity


def compute_debt_to_assets(total_debt: float, total_assets: float) -> float:
    """Compute Debt-to-Assets ratio."""
    if total_assets <= 0 or pd.isna(total_assets):
        return np.nan
    return total_debt / total_assets


def compute_interest_coverage(ebit: float, interest_expense: float) -> float:
    """Compute Interest Coverage ratio."""
    if interest_expense <= 0 or pd.isna(interest_expense):
        return np.nan
    return ebit / interest_expense


def compute_current_ratio(current_assets: float, current_liabilities: float) -> float:
    """Compute Current ratio."""
    if current_liabilities <= 0 or pd.isna(current_liabilities):
        return np.nan
    return current_assets / current_liabilities


def compute_quick_ratio(
    current_assets: float,
    inventory: float,
    current_liabilities: float
) -> float:
    """Compute Quick (Acid-Test) ratio."""
    if current_liabilities <= 0 or pd.isna(current_liabilities):
        return np.nan
    return (current_assets - inventory) / current_liabilities


# ==============================================================================
# EFFICIENCY RATIOS
# ==============================================================================

def compute_asset_turnover(revenue: float, avg_total_assets: float) -> float:
    """Compute Asset Turnover ratio."""
    if avg_total_assets <= 0 or pd.isna(avg_total_assets):
        return np.nan
    return revenue / avg_total_assets


def compute_inventory_turnover(cogs: float, avg_inventory: float) -> float:
    """Compute Inventory Turnover ratio."""
    if avg_inventory <= 0 or pd.isna(avg_inventory):
        return np.nan
    return cogs / avg_inventory


def compute_receivables_turnover(revenue: float, avg_receivables: float) -> float:
    """Compute Receivables Turnover ratio."""
    if avg_receivables <= 0 or pd.isna(avg_receivables):
        return np.nan
    return revenue / avg_receivables


def compute_days_sales_outstanding(avg_receivables: float, revenue: float) -> float:
    """Compute Days Sales Outstanding (DSO)."""
    if revenue <= 0 or pd.isna(revenue):
        return np.nan
    return (avg_receivables / revenue) * 365


# ==============================================================================
# GROWTH METRICS
# ==============================================================================

def compute_revenue_growth(current_revenue: float, prior_revenue: float) -> float:
    """Compute Revenue Growth rate."""
    if prior_revenue <= 0 or pd.isna(prior_revenue):
        return np.nan
    return (current_revenue - prior_revenue) / prior_revenue


def compute_earnings_growth(current_eps: float, prior_eps: float) -> float:
    """Compute Earnings Growth rate."""
    if prior_eps == 0 or pd.isna(prior_eps):
        return np.nan
    return (current_eps - prior_eps) / abs(prior_eps)


def compute_cagr(start_value: float, end_value: float, years: int) -> float:
    """Compute Compound Annual Growth Rate."""
    if start_value <= 0 or pd.isna(start_value) or years <= 0:
        return np.nan
    return (end_value / start_value) ** (1 / years) - 1


# ==============================================================================
# CASH FLOW METRICS
# ==============================================================================

def compute_fcf_yield(free_cash_flow: float, market_cap: float) -> float:
    """Compute Free Cash Flow Yield."""
    if market_cap <= 0 or pd.isna(market_cap):
        return np.nan
    return free_cash_flow / market_cap


def compute_ocf_to_debt(operating_cash_flow: float, total_debt: float) -> float:
    """Compute Operating Cash Flow to Debt ratio."""
    if total_debt <= 0 or pd.isna(total_debt):
        return np.nan
    return operating_cash_flow / total_debt


def compute_capex_to_revenue(capex: float, revenue: float) -> float:
    """Compute CapEx as percentage of Revenue."""
    if revenue <= 0 or pd.isna(revenue):
        return np.nan
    return abs(capex) / revenue


# ==============================================================================
# QUALITY SCORES
# ==============================================================================

def compute_piotroski_fscore(fundamentals: Dict) -> int:
    """
    Compute Piotroski F-Score (0-9).
    
    Args:
        fundamentals: Dict with required financial data:
            - net_income, roa, roa_prior
            - operating_cash_flow
            - leverage, leverage_prior
            - current_ratio, current_ratio_prior
            - shares_outstanding, shares_outstanding_prior
            - gross_margin, gross_margin_prior
            - asset_turnover, asset_turnover_prior
            
    Returns:
        F-Score (0-9)
    """
    score = 0
    
    # Profitability
    if fundamentals.get('net_income', 0) > 0:
        score += 1
    if fundamentals.get('roa', 0) > 0:
        score += 1
    if fundamentals.get('operating_cash_flow', 0) > 0:
        score += 1
    if fundamentals.get('operating_cash_flow', 0) > fundamentals.get('net_income', 0):
        score += 1
    
    # Leverage & Liquidity
    if fundamentals.get('leverage', 1) < fundamentals.get('leverage_prior', 1):
        score += 1
    if fundamentals.get('current_ratio', 0) > fundamentals.get('current_ratio_prior', 0):
        score += 1
    if fundamentals.get('shares_outstanding', 1) <= fundamentals.get('shares_outstanding_prior', 1):
        score += 1
    
    # Operating Efficiency
    if fundamentals.get('gross_margin', 0) > fundamentals.get('gross_margin_prior', 0):
        score += 1
    if fundamentals.get('asset_turnover', 0) > fundamentals.get('asset_turnover_prior', 0):
        score += 1
    
    return score


def compute_altman_zscore(
    working_capital: float,
    retained_earnings: float,
    ebit: float,
    market_cap: float,
    total_liabilities: float,
    sales: float,
    total_assets: float
) -> float:
    """
    Compute Altman Z-Score (bankruptcy predictor).
    
    Z > 2.99: Safe zone
    1.81 < Z < 2.99: Grey zone
    Z < 1.81: Distress zone
    """
    if total_assets <= 0 or pd.isna(total_assets):
        return np.nan
    if total_liabilities <= 0:
        total_liabilities = 1  # Avoid division by zero
    
    A = working_capital / total_assets
    B = retained_earnings / total_assets
    C = ebit / total_assets
    D = market_cap / total_liabilities
    E = sales / total_assets
    
    return 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E


# ==============================================================================
# DATA FETCHING
# ==============================================================================

def fetch_fundamentals(ticker: str) -> Dict:
    """
    Fetch fundamental data for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dict with fundamental metrics
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get financial statements
        balance_sheet = stock.balance_sheet
        income_stmt = stock.financials
        cash_flow = stock.cashflow
        
        # Extract key values
        fundamentals = {
            'ticker': ticker,
            'price': info.get('currentPrice', info.get('regularMarketPrice')),
            'market_cap': info.get('marketCap'),
            'enterprise_value': info.get('enterpriseValue'),
            
            # Valuation
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'pb_ratio': info.get('priceToBook'),
            'ps_ratio': info.get('priceToSalesTrailing12Months'),
            'peg_ratio': info.get('pegRatio'),
            'ev_ebitda': info.get('enterpriseToEbitda'),
            'ev_revenue': info.get('enterpriseToRevenue'),
            
            # Profitability
            'gross_margin': info.get('grossMargins'),
            'operating_margin': info.get('operatingMargins'),
            'net_margin': info.get('profitMargins'),
            'roe': info.get('returnOnEquity'),
            'roa': info.get('returnOnAssets'),
            
            # Growth
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth'),
            
            # Leverage
            'debt_to_equity': info.get('debtToEquity'),
            'current_ratio': info.get('currentRatio'),
            'quick_ratio': info.get('quickRatio'),
            
            # Per Share
            'eps': info.get('trailingEps'),
            'forward_eps': info.get('forwardEps'),
            'book_value': info.get('bookValue'),
            'revenue_per_share': info.get('revenuePerShare'),
            
            # Dividends
            'dividend_yield': info.get('dividendYield'),
            'dividend_rate': info.get('dividendRate'),
            'payout_ratio': info.get('payoutRatio'),
            
            # Cash Flow
            'operating_cash_flow': info.get('operatingCashflow'),
            'free_cash_flow': info.get('freeCashflow'),
            
            # Other
            'beta': info.get('beta'),
            'shares_outstanding': info.get('sharesOutstanding'),
            'float_shares': info.get('floatShares'),
            'short_ratio': info.get('shortRatio'),
            'short_percent_of_float': info.get('shortPercentOfFloat'),
        }
        
        # Extract from financial statements if available
        if balance_sheet is not None and not balance_sheet.empty:
            latest = balance_sheet.iloc[:, 0]
            fundamentals['total_assets'] = latest.get('Total Assets')
            fundamentals['total_liabilities'] = latest.get('Total Liabilities Net Minority Interest')
            fundamentals['shareholders_equity'] = latest.get('Stockholders Equity')
        
        if income_stmt is not None and not income_stmt.empty:
            latest = income_stmt.iloc[:, 0]
            fundamentals['revenue'] = latest.get('Total Revenue')
            fundamentals['gross_profit'] = latest.get('Gross Profit')
            fundamentals['operating_income'] = latest.get('Operating Income')
            fundamentals['net_income'] = latest.get('Net Income')
            fundamentals['ebitda'] = latest.get('EBITDA')
        
        return fundamentals
        
    except Exception as e:
        logger.error(f"Failed to fetch fundamentals for {ticker}: {e}")
        return {'ticker': ticker, 'error': str(e)}


def compute_all_fundamental_features(fundamentals: Dict) -> Dict:
    """
    Compute all derived fundamental features from raw fundamentals.
    
    Args:
        fundamentals: Raw fundamental data dict
        
    Returns:
        Dict with computed fundamental features
    """
    features = {}
    
    # Valuation features
    if fundamentals.get('pe_ratio'):
        features['pe_ratio'] = fundamentals['pe_ratio']
        features['pe_zscore'] = 0  # Would need sector data for comparison
    
    if fundamentals.get('pb_ratio'):
        features['pb_ratio'] = fundamentals['pb_ratio']
    
    if fundamentals.get('ps_ratio'):
        features['ps_ratio'] = fundamentals['ps_ratio']
    
    if fundamentals.get('ev_ebitda'):
        features['ev_ebitda'] = fundamentals['ev_ebitda']
    
    # Profitability features
    if fundamentals.get('gross_margin') is not None:
        features['gross_margin'] = fundamentals['gross_margin']
    
    if fundamentals.get('operating_margin') is not None:
        features['operating_margin'] = fundamentals['operating_margin']
    
    if fundamentals.get('net_margin') is not None:
        features['net_margin'] = fundamentals['net_margin']
    
    if fundamentals.get('roe') is not None:
        features['roe'] = fundamentals['roe']
    
    if fundamentals.get('roa') is not None:
        features['roa'] = fundamentals['roa']
    
    # Growth features
    if fundamentals.get('revenue_growth') is not None:
        features['revenue_growth'] = fundamentals['revenue_growth']
    
    if fundamentals.get('earnings_growth') is not None:
        features['earnings_growth'] = fundamentals['earnings_growth']
    
    # Leverage features
    if fundamentals.get('debt_to_equity') is not None:
        features['debt_to_equity'] = fundamentals['debt_to_equity']
    
    if fundamentals.get('current_ratio') is not None:
        features['current_ratio'] = fundamentals['current_ratio']
    
    # Cash flow features
    if fundamentals.get('free_cash_flow') and fundamentals.get('market_cap'):
        features['fcf_yield'] = compute_fcf_yield(
            fundamentals['free_cash_flow'],
            fundamentals['market_cap']
        )
    
    # Quality scores
    if all(k in fundamentals for k in ['net_income', 'roa', 'operating_cash_flow']):
        features['piotroski_fscore'] = compute_piotroski_fscore(fundamentals)
    
    # Risk metrics
    if fundamentals.get('beta') is not None:
        features['beta'] = fundamentals['beta']
    
    if fundamentals.get('short_ratio') is not None:
        features['short_ratio'] = fundamentals['short_ratio']
    
    return features
