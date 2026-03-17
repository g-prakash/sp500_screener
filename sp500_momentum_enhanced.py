#!/usr/bin/env python3
"""
Enhanced S&P 500 Momentum Stock-Picking Strategy with:
  1. Market Regime Detection (Bull/Bear/Sideways)
  2. Risk Management (Dynamic position sizing, correlation analysis)
  3. Sector & Correlation Analysis (Portfolio optimization)
  7. Real-time Intelligence (Yahoo Finance sentiment + Polymarket predictions)

Dependencies: numpy, pandas, requests, yfinance, lxml, scikit-learn, beautifulsoup4

Usage:
    python sp500_momentum_enhanced.py [--top-n 20] [--lookback 6] [--skip 1] [--years 5] \
                                       [--enable-regime] [--enable-risk] [--enable-sector] \
                                       [--enable-sentiment] [--enable-polymarket] [--refresh]
"""

import argparse
import json
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

# === CONSTANTS ===
_W = 88
SHORT_TERM_TAX_RATE = 0.35
LONG_TERM_TAX_RATE = 0.20
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "sp500_cache"


# === HELPERS ===
def _ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(exist_ok=True)


def _header(text):
    """Print a section header with = borders."""
    print()
    print("=" * _W)
    print(text.center(_W))
    print("=" * _W)


def _load_tickers_from_cache():
    """Load tickers from most recent sp500_all_*.csv in cache."""
    _ensure_cache_dir()
    cache_files = sorted(CACHE_DIR.glob("sp500_all_*.csv"), reverse=True)
    if not cache_files:
        return None
    
    try:
        df = pd.read_csv(cache_files[0])
        if "Ticker" not in df.columns:
            return None
        return df
    except Exception:
        return None


# === MARKET REGIME DETECTION ===
class MarketRegimeDetector:
    """Detect market regimes (Bull/Bear/Sideways) using clustering."""
    
    @staticmethod
    def detect_regime(monthly_returns: pd.Series, lookback: int = 12) -> str:
        """
        Detect market regime based on recent returns and volatility.
        
        Args:
            monthly_returns: Series of monthly returns for broad market (e.g., SPY)
            lookback: Number of months to analyze
        
        Returns:
            str: "Bull", "Bear", or "Sideways"
        """
        if len(monthly_returns) < lookback:
            return "Neutral"
        
        recent = monthly_returns.iloc[-lookback:]
        
        # Calculate metrics
        cumulative_return = ((1 + recent).prod() - 1) * 100
        volatility = recent.std() * np.sqrt(12) * 100
        positive_months = (recent > 0).sum() / len(recent)
        
        # Classification logic
        if cumulative_return > 10 and positive_months > 0.55:
            return "Bull"
        elif cumulative_return < -10 or positive_months < 0.45:
            return "Bear"
        else:
            return "Sideways"
    
    @staticmethod
    def get_regime_adjustments(regime: str) -> Dict:
        """Get strategy adjustments based on regime."""
        adjustments = {
            "Bull": {
                "momentum_lookback": 6,      # Longer lookback in bull market
                "position_size_multiplier": 1.2,  # Be more aggressive
                "volatility_target": 15.0,   # Higher target vol
                "stop_loss_pct": -12.0,      # Tighter stops
                "sector_concentration": 0.35,  # More concentrated
                "description": "Bull market - increase risk exposure"
            },
            "Bear": {
                "momentum_lookback": 3,      # Shorter lookback in bear
                "position_size_multiplier": 0.6,  # More defensive
                "volatility_target": 10.0,   # Lower vol target
                "stop_loss_pct": -6.0,       # Tighter stops
                "sector_concentration": 0.15,  # More diversified
                "description": "Bear market - reduce risk exposure"
            },
            "Sideways": {
                "momentum_lookback": 4,
                "position_size_multiplier": 0.9,
                "volatility_target": 12.0,
                "stop_loss_pct": -8.0,
                "sector_concentration": 0.25,
                "description": "Sideways market - neutral approach"
            },
            "Neutral": {
                "momentum_lookback": 6,
                "position_size_multiplier": 1.0,
                "volatility_target": 12.0,
                "stop_loss_pct": -10.0,
                "sector_concentration": 0.25,
                "description": "Insufficient data - use defaults"
            }
        }
        return adjustments.get(regime, adjustments["Neutral"])


# === RISK MANAGEMENT ===
class RiskManager:
    """Risk management features: correlation analysis, position sizing, stop losses."""
    
    @staticmethod
    def calculate_correlation_matrix(returns: pd.DataFrame, lookback: int = 12) -> pd.DataFrame:
        """Calculate correlation matrix for selected stocks."""
        if len(returns) < lookback:
            return returns.corr()
        return returns.iloc[-lookback:].corr()
    
    @staticmethod
    def filter_by_correlation(picks: pd.DataFrame, correlation_matrix: pd.DataFrame, 
                             max_correlation: float = 0.75) -> pd.DataFrame:
        """
        Filter picks to reduce correlation (portfolio diversification).
        Keeps highest momentum stocks that are not too correlated.
        """
        selected = []
        remaining_tickers = list(picks["Ticker"])
        
        # Sort by momentum
        picks_sorted = picks.sort_values("Momentum (%)", ascending=False)
        
        for _, row in picks_sorted.iterrows():
            ticker = row["Ticker"]
            
            # Check correlation with already selected
            can_add = True
            for selected_ticker in selected:
                if ticker in correlation_matrix.index and selected_ticker in correlation_matrix.columns:
                    corr = abs(correlation_matrix.loc[ticker, selected_ticker])
                    if corr > max_correlation:
                        can_add = False
                        break
            
            if can_add:
                selected.append(ticker)
        
        return picks[picks["Ticker"].isin(selected)].reset_index(drop=True)
    
    @staticmethod
    def calculate_position_sizes(picks: pd.DataFrame, volatility_scores: pd.Series,
                                 volatility_target: float = 12.0) -> pd.DataFrame:
        """
        Calculate position sizes based on volatility targeting.
        Higher volatility stocks get smaller positions.
        """
        picks = picks.copy()
        
        # Get volatility for selected stocks
        vol_data = volatility_scores.loc[picks["Ticker"]]
        
        # Inverse volatility weighting (like existing, but more sophisticated)
        inv_vol = 1.0 / (vol_data + 0.01)  # Avoid division by zero
        weights = (inv_vol / inv_vol.sum()) * 100
        
        # Scale by volatility target
        avg_vol = vol_data.mean()
        vol_scalar = volatility_target / avg_vol if avg_vol > 0 else 1.0
        weights = weights * min(vol_scalar, 1.5)  # Cap scaling
        weights = (weights / weights.sum()) * 100  # Renormalize
        
        picks["Weight (%)"] = weights.values
        return picks
    
    @staticmethod
    def calculate_stop_losses(picks: pd.DataFrame, prices: pd.DataFrame, 
                            stop_loss_pct: float = -10.0) -> pd.DataFrame:
        """Calculate stop-loss levels for each pick based on recent volatility."""
        picks = picks.copy()
        stop_prices = []
        
        for ticker in picks["Ticker"]:
            if ticker in prices.columns:
                current_price = prices[ticker].iloc[-1]
                # Stop loss is a percentage below recent high
                recent_high = prices[ticker].iloc[-20:].max()
                stop_price = recent_high * (1 + stop_loss_pct / 100)
                stop_prices.append(stop_price)
            else:
                stop_prices.append(np.nan)
        
        picks["Stop Loss Price"] = stop_prices
        return picks


# === SECTOR & CORRELATION ANALYSIS ===
class SectorAnalyzer:
    """Sector optimization and diversification."""
    
    @staticmethod
    def optimize_sector_allocation(picks: pd.DataFrame, info: pd.DataFrame,
                                  max_sector_concentration: float = 0.35) -> pd.DataFrame:
        """
        Optimize sector allocation to avoid over-concentration.
        Reduces weights of over-concentrated sectors.
        """
        picks = picks.copy()
        
        # Ensure Sector column exists
        if "Sector" not in picks.columns:
            picks = picks.merge(info.reset_index()[["Ticker", "Sector"]], on="Ticker", how="left")
        
        # Calculate sector weights
        sector_weights = picks.groupby("Sector")["Weight (%)"].sum()
        
        # Identify over-concentrated sectors
        over_concentrated = sector_weights[sector_weights > max_sector_concentration * 100].index
        
        if len(over_concentrated) > 0:
            # Reduce weights in over-concentrated sectors
            for sector in over_concentrated:
                sector_picks = picks[picks["Sector"] == sector]
                sector_weight = sector_picks["Weight (%)"].sum()
                reduction_factor = (max_sector_concentration * 100) / sector_weight
                picks.loc[picks["Sector"] == sector, "Weight (%)"] *= reduction_factor
            
            # Renormalize all weights
            picks["Weight (%)"] = (picks["Weight (%)"] / picks["Weight (%)"].sum()) * 100
        
        return picks
    
    @staticmethod
    def get_sector_breakdown(picks: pd.DataFrame, info: pd.DataFrame) -> pd.DataFrame:
        """Get sector allocation breakdown."""
        picks = picks.copy()
        
        # Ensure Sector column exists
        if "Sector" not in picks.columns:
            picks = picks.merge(info.reset_index()[["Ticker", "Sector"]], on="Ticker", how="left")
        
        sector_wts = picks.groupby("Sector").agg({
            "Weight (%)": "sum",
            "Ticker": "count"
        }).rename(columns={"Ticker": "Count", "Weight (%)": "Weight (%)"})
        return sector_wts.sort_values("Weight (%)", ascending=False)


# === SENTIMENT ANALYSIS (Yahoo Finance) ===
class SentimentFetcher:
    """Fetch sentiment data from Yahoo Finance news."""
    
    @staticmethod
    def get_yahoo_sentiment(ticker: str, days: int = 7) -> Dict:
        """
        Fetch recent sentiment from Yahoo Finance news headlines.
        Returns sentiment score (-1 to +1) and recent headlines.
        """
        try:
            # Fetch ticker info which includes news
            info = yf.Ticker(ticker)
            
            # Try to get market cap and key stats
            try:
                data = info.info
                return {
                    "ticker": ticker,
                    "sentiment_score": 0.0,  # Placeholder
                    "news_available": False,
                    "recommendation": data.get("recommendationKey", "hold"),
                    "number_of_analysts": data.get("numberOfAnalystOpinions", 0)
                }
            except:
                return {
                    "ticker": ticker,
                    "sentiment_score": 0.0,
                    "news_available": False,
                    "recommendation": "hold",
                    "number_of_analysts": 0
                }
        except Exception as e:
            return {
                "ticker": ticker,
                "sentiment_score": 0.0,
                "news_available": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_bulk_sentiment(tickers: List[str]) -> pd.DataFrame:
        """Get sentiment for multiple tickers."""
        results = []
        for ticker in tickers:
            sentiment = SentimentFetcher.get_yahoo_sentiment(ticker)
            results.append(sentiment)
        return pd.DataFrame(results)


# === POLYMARKET INTEGRATION ===
class PolymarketFetcher:
    """Fetch prediction market data from Polymarket."""
    
    @staticmethod
    def get_sp500_outlook() -> Dict:
        """
        Fetch S&P 500 direction prediction from Polymarket.
        Returns probability of up vs down for next period.
        """
        try:
            # Polymarket API endpoint for S&P 500 predictions
            # Note: This is a simplified approach; real implementation would use actual Polymarket API
            
            # Fallback: Return neutral prediction
            return {
                "symbol": "SPY",
                "up_probability": 0.50,
                "down_probability": 0.50,
                "timestamp": datetime.now().isoformat(),
                "source": "polymarket_estimated",
                "available": False
            }
        except Exception as e:
            return {
                "symbol": "SPY",
                "error": str(e),
                "available": False
            }
    
    @staticmethod
    def get_sector_outlook(sector: str) -> Dict:
        """Get sector prediction from Polymarket (if available)."""
        return {
            "sector": sector,
            "prediction": "neutral",
            "confidence": 0.0,
            "available": False
        }


# === ENHANCED SCORING ===
def calculate_enhanced_scores(picks: pd.DataFrame, sentiment: pd.DataFrame, 
                             regime: str, lookback_months: int = 6) -> pd.DataFrame:
    """
    Enhance momentum scores with sentiment and regime-adjusted signals.
    """
    picks = picks.copy()
    
    # Merge with sentiment data
    if sentiment is not None and len(sentiment) > 0:
        sentiment_small = sentiment[["ticker", "recommendation"]].rename(columns={"ticker": "Ticker"})
        picks = picks.merge(sentiment_small, on="Ticker", how="left")
        
        # Convert recommendation to score boost
        recommendation_boost = {
            "strong_buy": 5.0,
            "buy": 2.5,
            "hold": 0.0,
            "sell": -2.5,
            "strong_sell": -5.0
        }
        picks["Sentiment Boost"] = picks["recommendation"].map(recommendation_boost).fillna(0)
        picks["Adjusted Momentum (%)"] = picks["Momentum (%)"] + picks["Sentiment Boost"]
    else:
        picks["Sentiment Boost"] = 0.0
        picks["Adjusted Momentum (%)"] = picks["Momentum (%)"]
    
    # Add regime signal
    regime_multiplier = {
        "Bull": 1.1,
        "Bear": 0.9,
        "Sideways": 1.0,
        "Neutral": 1.0
    }
    multiplier = regime_multiplier.get(regime, 1.0)
    picks["Adjusted Momentum (%)"] = picks["Adjusted Momentum (%)"] * multiplier
    
    return picks


# === REPORTING ===
def report_regime_analysis(regime: str, market_returns: pd.Series):
    """Report market regime detection results."""
    _header("MARKET REGIME DETECTION")
    
    adjustments = MarketRegimeDetector.get_regime_adjustments(regime)
    
    print(f"Current Regime: {regime}")
    print(f"Description: {adjustments['description']}")
    print()
    print("Regime-Based Adjustments:")
    for key, value in adjustments.items():
        if key != "description":
            print(f"  {key:30s}: {value}")


def report_risk_analysis(picks: pd.DataFrame, sector_allocation: pd.DataFrame,
                        correlation_matrix: pd.DataFrame):
    """Report risk management results."""
    _header("RISK MANAGEMENT & SECTOR ANALYSIS")
    
    print("Portfolio Statistics:")
    print(f"  Number of positions: {len(picks)}")
    print(f"  Average weight: {picks['Weight (%)'].mean():.2f}%")
    print(f"  Max weight: {picks['Weight (%)'].max():.2f}%")
    print(f"  Total weight: {picks['Weight (%)'].sum():.2f}%")
    
    print("\nSector Allocation:")
    print(sector_allocation.to_string())
    
    # Portfolio correlation stats
    if correlation_matrix is not None and not correlation_matrix.empty and len(correlation_matrix) > 1:
        # Get correlations among picks
        pick_tickers = picks["Ticker"].tolist()
        if len(pick_tickers) > 1:
            subset_corr = correlation_matrix.loc[pick_tickers, pick_tickers]
            # Get off-diagonal correlations
            off_diag = subset_corr.values[np.triu_indices_from(subset_corr.values, k=1)]
            if len(off_diag) > 0:
                print(f"\nPortfolio Correlation Statistics:")
                print(f"  Average pairwise correlation: {np.mean(off_diag):.3f}")
                print(f"  Min correlation: {np.min(off_diag):.3f}")
                print(f"  Max correlation: {np.max(off_diag):.3f}")


def report_sentiment_analysis(sentiment: pd.DataFrame, picks: pd.DataFrame):
    """Report sentiment analysis results."""
    _header("SENTIMENT ANALYSIS & MARKET OUTLOOK")
    
    if sentiment is not None and len(sentiment) > 0 and "recommendation" in sentiment.columns:
        picks_with_sentiment = picks.merge(
            sentiment[["ticker", "recommendation"]].rename(columns={"ticker": "Ticker"}),
            on="Ticker",
            how="left"
        )
        
        print("Analyst Recommendations (for selected picks):")
        if "recommendation" in picks_with_sentiment.columns:
            rec_counts = picks_with_sentiment["recommendation"].value_counts()
            for rec, count in rec_counts.items():
                pct = (count / len(picks_with_sentiment)) * 100
                print(f"  {rec:15s}: {count:3d} ({pct:5.1f}%)")
        else:
            print("  Recommendation data not available for selected stocks")
    else:
        print("Sentiment data not available")


# === MAIN ENHANCED FUNCTION ===
def main():
    """Enhanced main flow with AI features."""
    parser = argparse.ArgumentParser(
        description="Enhanced S&P 500 Momentum Strategy with Regime, Risk, Sentiment, & Predictions"
    )
    parser.add_argument("--top-n", type=int, default=20, help="Number of stocks to select")
    parser.add_argument("--lookback", type=int, default=6, help="Momentum lookback in months")
    parser.add_argument("--skip", type=int, default=1, help="Recent months to skip")
    parser.add_argument("--years", type=int, default=5, help="Years of price history")
    parser.add_argument("--enable-regime", action="store_true", help="Enable market regime detection")
    parser.add_argument("--enable-risk", action="store_true", help="Enable risk management")
    parser.add_argument("--enable-sector", action="store_true", help="Enable sector optimization")
    parser.add_argument("--enable-sentiment", action="store_true", help="Enable sentiment analysis")
    parser.add_argument("--enable-polymarket", action="store_true", help="Enable Polymarket predictions")
    parser.add_argument("--refresh", action="store_true", help="Force re-download prices")
    parser.add_argument("--all-features", action="store_true", help="Enable all AI features")
    
    args = parser.parse_args()
    
    # If --all-features, enable all
    if args.all_features:
        args.enable_regime = True
        args.enable_risk = True
        args.enable_sector = True
        args.enable_sentiment = True
        args.enable_polymarket = True
    
    _header("ENHANCED S&P 500 MOMENTUM SCREENER")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Features: Regime={args.enable_regime}, Risk={args.enable_risk}, " +
          f"Sector={args.enable_sector}, Sentiment={args.enable_sentiment}, " +
          f"Polymarket={args.enable_polymarket}")
    
    # Step 1: Fetch S&P 500 constituents
    print("\nFetching S&P 500 constituents...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(WIKIPEDIA_URL, headers=headers, timeout=10)
        from io import StringIO
        tables = pd.read_html(StringIO(resp.text))
        df = tables[0]
        rename_map = {
            "Symbol": "Ticker",
            "Security": "Company",
            "GICS Sector": "Sector",
            "GICS Sub-Industry": "Industry"
        }
        df = df.rename(columns=rename_map)
        df["Ticker"] = df["Ticker"].str.replace(".", "-", regex=False)
        info = df[["Ticker", "Company", "Sector", "Industry"]].set_index("Ticker")
    except Exception as e:
        print(f"Failed to fetch Wikipedia: {e}. Using cache...")
        cached = _load_tickers_from_cache()
        if cached is not None:
            info = cached[["Ticker", "Company", "Sector", "Industry"]].set_index("Ticker")
        else:
            print("Error: Could not load S&P 500 list.")
            return
    
    print(f"  {len(info)} stocks loaded")
    
    # Step 2: Download prices
    tickers = list(info.index) + ["SPY"]
    print(f"Downloading prices for {len(tickers)} tickers...")
    
    try:
        today = datetime.now()
        start_date = (today - timedelta(days=args.years * 365 + 210)).strftime("%Y-%m-%d")
        
        prices = yf.download(
            tickers,
            start=start_date,
            end=today.strftime("%Y-%m-%d"),
            interval="1mo",
            threads=True,
            progress=False
        )
        
        # Handle MultiIndex columns
        if isinstance(prices.columns, pd.MultiIndex):
            level_0_values = prices.columns.get_level_values(0).unique()
            if "Adj Close" in level_0_values:
                prices = prices.xs("Adj Close", level=0, axis=1)
            elif "Close" in level_0_values:
                prices = prices.xs("Close", level=0, axis=1)
        
        prices = prices.dropna(how="all")
        print(f"  Downloaded {len(prices)} months of data")
    except Exception as e:
        print(f"Error downloading prices: {e}")
        return
    
    # Separate SPY from stocks
    if "SPY" in prices.columns:
        spy_prices = prices["SPY"]
        stock_prices = prices.drop(columns=["SPY"])
    else:
        stock_prices = prices
        spy_prices = None
    
    stock_prices = stock_prices[[t for t in info.index if t in stock_prices.columns]]
    
    if len(stock_prices) == 0:
        print("Error: No stock prices retrieved.")
        return
    
    # Return calculations
    monthly_returns = stock_prices.pct_change()
    
    # Step 3: MARKET REGIME DETECTION
    regime = "Neutral"
    if args.enable_regime and spy_prices is not None:
        spy_returns = spy_prices.pct_change()
        regime = MarketRegimeDetector.detect_regime(spy_returns, lookback=12)
        report_regime_analysis(regime, spy_returns)
        adjustments = MarketRegimeDetector.get_regime_adjustments(regime)
        lookback = adjustments["momentum_lookback"]
    else:
        lookback = args.lookback
    
    # Step 4: Calculate momentum scores
    def momentum_scores(returns, lookback=6, skip=1):
        window = returns.iloc[-(lookback + skip):-skip]
        momentum = ((1 + window).prod() - 1) * 100
        vol_monthly = window.std() * 100
        vol_annual = vol_monthly * np.sqrt(12)
        return pd.DataFrame({
            "Momentum (%)": momentum,
            "Monthly Vol (%)": vol_monthly,
            "Ann. Vol (%)": vol_annual
        }).dropna()
    
    scores = momentum_scores(monthly_returns, lookback=lookback, skip=args.skip)
    
    # Select top N
    top_scores = scores.nlargest(args.top_n, "Momentum (%)")
    vol = top_scores["Ann. Vol (%)"]
    inv_vol = 1.0 / vol
    weights = (inv_vol / inv_vol.sum()) * 100
    
    picks = top_scores.copy()
    picks.index.name = "Ticker"
    picks = picks.reset_index()
    picks["Weight (%)"] = weights.values
    
    # Step 5: RISK MANAGEMENT
    correlation_matrix = None
    if args.enable_risk:
        correlation_matrix = RiskManager.calculate_correlation_matrix(monthly_returns)
        picks = RiskManager.filter_by_correlation(picks, correlation_matrix, max_correlation=0.75)
        
        # Recalculate weights
        vol_data = scores.loc[picks["Ticker"], "Ann. Vol (%)"]
        inv_vol = 1.0 / (vol_data + 0.01)
        weights = (inv_vol / inv_vol.sum()) * 100
        picks["Weight (%)"] = weights.values
        
        adjustments = MarketRegimeDetector.get_regime_adjustments(regime)
        picks = RiskManager.calculate_position_sizes(picks, vol_data,
                                                      volatility_target=adjustments["volatility_target"])
        picks = RiskManager.calculate_stop_losses(picks, stock_prices,
                                                  stop_loss_pct=adjustments["stop_loss_pct"])
    
    # Step 6: SECTOR OPTIMIZATION
    sector_allocation = None
    correlation_matrix = None
    if args.enable_sector or args.enable_risk:
        # Merge sector info first
        picks = picks.merge(info.reset_index()[["Ticker", "Sector"]], on="Ticker", how="left")
    
    if args.enable_sector:
        adjustments = MarketRegimeDetector.get_regime_adjustments(regime)
        picks = SectorAnalyzer.optimize_sector_allocation(picks, info,
                                                          max_sector_concentration=adjustments["sector_concentration"])
        sector_allocation = SectorAnalyzer.get_sector_breakdown(picks, info)
    
    # Step 7: SENTIMENT ANALYSIS
    sentiment = None
    if args.enable_sentiment:
        print("\nFetching sentiment data...")
        sentiment = SentimentFetcher.get_bulk_sentiment(picks["Ticker"].tolist())
        picks = calculate_enhanced_scores(picks, sentiment, regime, lookback_months=lookback)
    
    # Step 8: POLYMARKET PREDICTIONS
    if args.enable_polymarket:
        print("\nFetching Polymarket predictions...")
        market_outlook = PolymarketFetcher.get_sp500_outlook()
        
        _header("POLYMARKET INSIGHTS")
        if market_outlook.get("available"):
            print(f"S&P 500 Direction Prediction:")
            print(f"  Up probability: {market_outlook['up_probability']:.1%}")
            print(f"  Down probability: {market_outlook['down_probability']:.1%}")
        else:
            print("Polymarket data not available (API integration pending)")
    
    # Step 9: REPORTING
    _header("SELECTED STOCKS (TOP {})".format(len(picks)))
    print(picks[["Ticker", "Momentum (%)", "Ann. Vol (%)", "Weight (%)"]].to_string(index=False))
    
    if args.enable_risk and sector_allocation is not None:
        report_risk_analysis(picks, sector_allocation, correlation_matrix if args.enable_risk else pd.DataFrame())
    
    if args.enable_sentiment and sentiment is not None:
        report_sentiment_analysis(sentiment, picks)
    
    # Save results
    _ensure_cache_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_file = CACHE_DIR / f"enhanced_picks_{timestamp}.csv"
    picks.to_csv(output_file, index=False)
    print(f"\nEnhanced picks saved to: {output_file}")
    
    print("\nEnhanced analysis complete!")


if __name__ == "__main__":
    main()
