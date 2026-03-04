#!/usr/bin/env python3
"""
S&P 500 Momentum Stock-Picking Strategy with Backtesting and Tax Analysis.

Dependencies: numpy, pandas, requests, yfinance, lxml

Usage:
    python sp500_momentum.py [--top-n 20] [--lookback 6] [--skip 1] [--years 5] \
                             [--min-cap FLOAT] [--output PATH] [--no-backtest] \
                             [--apply-tax] [--refresh]
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# === CONSTANTS ===
_W = 88
SHORT_TERM_TAX_RATE = 0.35
LONG_TERM_TAX_RATE = 0.20
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Cache directory (sibling of script)
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


def _load_previous_picks():
    """Load the most recent picks_*.csv from cache."""
    _ensure_cache_dir()
    picks_files = sorted(CACHE_DIR.glob("picks_*.csv"), reverse=True)
    if not picks_files:
        return None
    
    try:
        df = pd.read_csv(picks_files[0], comment="#")
        return df
    except Exception:
        return None


# === S&P 500 CONSTITUENTS ===
def get_sp500_info():
    """
    Fetch current S&P 500 member list from Wikipedia.
    
    Returns:
        DataFrame indexed by Ticker with columns: Company, Sector, Industry.
    
    Raises:
        RuntimeError: If both Wikipedia and cache fail.
    """
    # Try Wikipedia
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(WIKIPEDIA_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        
        from io import StringIO
        tables = pd.read_html(StringIO(resp.text))
        df = tables[0]
        
        # Rename columns
        rename_map = {
            "Symbol": "Ticker",
            "Security": "Company",
            "GICS Sector": "Sector",
            "GICS Sub-Industry": "Industry"
        }
        df = df.rename(columns=rename_map)
        
        # Replace dots with hyphens in ticker
        df["Ticker"] = df["Ticker"].str.replace(".", "-", regex=False)
        
        # Keep relevant columns
        df = df[["Ticker", "Company", "Sector", "Industry"]].set_index("Ticker")
        
        # Save to cache for fallback
        _ensure_cache_dir()
        timestamp = datetime.now().strftime("%Y%m%d")
        cache_path = CACHE_DIR / f"sp500_all_{timestamp}.csv"
        df.reset_index().to_csv(cache_path, index=False)
        
        return df
    
    except Exception as e:
        print(f"Warning: Failed to fetch Wikipedia ({e}). Trying cache...")
        pass
    
    # Fallback to cache
    cached = _load_tickers_from_cache()
    if cached is not None:
        print(f"Loaded from cache: {cached.shape[0]} tickers")
        cols_to_keep = ["Ticker", "Company", "Sector", "Industry"]
        cols_to_keep = [c for c in cols_to_keep if c in cached.columns]
        cached = cached[cols_to_keep].set_index("Ticker")
        return cached
    
    # Fallback: Create minimal S&P 500 list (top tickers)
    print("Creating minimal S&P 500 list with major stocks...")
    _ensure_cache_dir()
    minimal_sp500 = {
        "Ticker": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "JNJ", "V", 
                   "MA", "PG", "UNH", "WMT", "XOM", "JPM", "BAC", "GS", "MS", "C",
                   "INTC", "AMD", "CSCO", "CRM", "ADBE", "DDOG", "SNOW", "CRWD", "OKTA", "MDB",
                   "ORCL", "WDAY", "ZS", "NFLX", "DIS", "FOXA", "FOX", "CMC", "ROKU", "PINS",
                   "SNAP", "SQ", "PYPL", "DASH", "AXP", "DFS", "SYF", "COF", "CCL", "RCL",
                   "AAL", "DAL", "UAL", "SAVE", "SKU", "ULTA", "DLTR", "COST", "TJX", "LULU"],
        "Company": ["Apple", "Microsoft", "NVIDIA", "Alphabet", "Amazon", "Meta", "Tesla", "Berkshire Hathaway", 
                    "Johnson & Johnson", "Visa"] + [""] * 50,
        "Sector": ["Information Technology", "Information Technology", "Information Technology", 
                   "Information Technology", "Consumer Cyclical", "Communication Services", "Consumer Cyclical",
                   "Financial", "Healthcare", "Financial Services"] + [""] * 50,
        "Industry": ["Computer Hardware", "Software", "Semiconductors", "Internet", "Retail", "Internet",
                     "Auto Manufacturers", "Insurance", "Healthcare", "Financial Services"] + [""] * 50
    }
    minimal_df = pd.DataFrame(minimal_sp500).set_index("Ticker")
    
    # Save to cache
    timestamp = datetime.now().strftime("%Y%m%d")
    cache_path = CACHE_DIR / f"sp500_all_{timestamp}.csv"
    minimal_df.reset_index().to_csv(cache_path, index=False)
    
    return minimal_df


# === PRICE DATA ===
def fetch_monthly_prices(tickers, years=5, refresh=False):
    """
    Download monthly adjusted-close prices via yfinance.
    
    Args:
        tickers: List of ticker symbols.
        years: Historical years to download.
        refresh: If True, force re-download; else use cache if available.
    
    Returns:
        DataFrame with Date index and ticker columns (Adj Close).
    """
    _ensure_cache_dir()
    
    # Compute date range
    today = datetime.now()
    start_date = today - timedelta(days=years * 365 + 210)
    start_str = start_date.strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    # Check cache
    cache_pattern = f"monthly_{start_date.strftime('%Y%m')}_{today.strftime('%Y%m')}.csv"
    cache_path = CACHE_DIR / cache_pattern
    
    if cache_path.exists() and not refresh:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df
    
    # Download
    print(f"Downloading {len(tickers)} tickers (monthly)...")
    prices = yf.download(
        tickers,
        start=start_str,
        end=today_str,
        interval="1mo",
        threads=True,
        progress=True
    )
    
    # Handle MultiIndex columns (multiple tickers)
    # yfinance returns columns like (Adj Close, AAPL), (Close, MSFT), etc.
    if isinstance(prices.columns, pd.MultiIndex):
        # Get the first level names
        level_0_values = prices.columns.get_level_values(0).unique()
        
        # Look for Adj Close or Close
        if "Adj Close" in level_0_values:
            prices = prices.xs("Adj Close", level=0, axis=1)
        elif "Close" in level_0_values:
            prices = prices.xs("Close", level=0, axis=1)
        else:
            # Use the first level available
            first_level = level_0_values[0]
            prices = prices.xs(first_level, level=0, axis=1)
    elif isinstance(prices.columns, pd.Index):
        # Single ticker case - already has standard columns
        pass
    
    # Drop all-NaN rows
    prices = prices.dropna(how="all")
    
    # Drop current (incomplete) month if matches today's month
    if len(prices) > 0:
        last_date = prices.index[-1]
        if last_date.year == today.year and last_date.month == today.month:
            prices = prices.iloc[:-1]
    
    # Save to cache
    prices.to_csv(cache_path)
    
    return prices


# === MOMENTUM SCORING ===
def momentum_scores(monthly_returns, lookback=6, skip=1):
    """
    Compute momentum scores from monthly returns.
    
    Args:
        monthly_returns: DataFrame of monthly returns (from prices.pct_change()).
        lookback: Window size in months.
        skip: Months to skip at the end (avoids recent mean-reversion).
    
    Returns:
        DataFrame indexed by Ticker with Momentum (%), Monthly Vol (%), Ann. Vol (%).
    """
    window = monthly_returns.iloc[-(lookback + skip):-skip]
    
    # Cumulative return
    momentum = ((1 + window).prod() - 1) * 100
    
    # Monthly volatility
    vol_monthly = window.std() * 100
    
    # Annualized volatility
    vol_annual = vol_monthly * np.sqrt(12)
    
    result = pd.DataFrame({
        "Momentum (%)": momentum,
        "Monthly Vol (%)": vol_monthly,
        "Ann. Vol (%)": vol_annual
    })
    
    result = result.dropna()
    result.index.name = "Ticker"  # Ensure index has a name
    return result


# === SELECTION ===
def select_top(scores, top_n=20):
    """
    Select top N stocks by momentum and weight by inverse volatility.
    
    Args:
        scores: DataFrame from momentum_scores().
        top_n: Number of stocks to select.
    
    Returns:
        DataFrame with columns: Momentum (%), Vol, Weight (%).
    """
    # Sort by momentum, take top N
    top = scores.nlargest(top_n, "Momentum (%)")
    
    # Inverse volatility weights
    vol = top["Ann. Vol (%)"]
    inv_vol = 1.0 / vol
    weights = (inv_vol / inv_vol.sum()) * 100
    
    top = top.copy()
    top["Weight (%)"] = weights
    
    return top


# === BACKTEST ===
def run_backtest(monthly_returns, spy_returns, lookback=6, skip=1, top_n=10):
    """
    Walk forward backtesting month-by-month.
    
    Args:
        monthly_returns: DataFrame of monthly returns (stock universe).
        spy_returns: Series of SPY monthly returns (benchmark).
        lookback, skip, top_n: Strategy parameters.
    
    Returns:
        DataFrame indexed by Date with Strategy and Benchmark columns.
    """
    results = []
    
   # Start from t = lookback + skip
    start_idx = lookback + skip
    
    for t in range(start_idx, len(monthly_returns)):
        # Window for scoring - get data from past (t-lookback-skip to t-skip)
        window = monthly_returns.iloc[t - lookback - skip:t - skip]
        
        if len(window) < lookback:
            # Not enough data
            continue
        
        # Momentum scores computed on the full window
        # We'll compute it directly
        momentum_vals = []
        vol_vals = []
        tickers = []
        
        for ticker in window.columns:
            ticker_returns = window[ticker].dropna()
            if len(ticker_returns) < lookback:
                continue
            
            # Take last lookback returns
            ticker_returns = ticker_returns.iloc[-lookback:]
            
            momentum = ((1 + ticker_returns).prod() - 1) * 100
            vol = ticker_returns.std() * np.sqrt(12) * 100
            
            momentum_vals.append(momentum)
            vol_vals.append(vol)
            tickers.append(ticker)
        
        if not tickers:
            continue
        
        # Create scores dataframe
        scores = pd.DataFrame({
            "Momentum (%)": momentum_vals,
            "Ann. Vol (%)": vol_vals
        }, index=tickers)
        scores.index.name = "Ticker"
        
        # Select top N
        top = select_top(scores, top_n=top_n)
        selected_tickers = top.index.tolist()
        weights = (top["Weight (%)"] / 100).to_dict()
        
        # Forward returns at month t
        forward_returns = monthly_returns.iloc[t]
        
        # Re-normalize weights to only valid tickers
        valid_tickers = [tk for tk in selected_tickers if tk in forward_returns.index and not pd.isna(forward_returns[tk])]
        if not valid_tickers:
            continue
        
        valid_weights = {tk: weights[tk] for tk in valid_tickers}
        weight_sum = sum(valid_weights.values())
        if weight_sum == 0:
            continue
        valid_weights = {tk: w / weight_sum for tk, w in valid_weights.items()}
        
        # Portfolio return
        portfolio_ret = sum(valid_weights[tk] * forward_returns[tk] for tk in valid_tickers)
        
        # Benchmark return (match by date)
        current_date = monthly_returns.index[t]
        spy_ret = None
        
        # Try exact match
        if current_date in spy_returns.index:
            spy_ret = spy_returns[current_date]
        else:
            # Match by year+month
            for spy_date in spy_returns.index:
                if spy_date.year == current_date.year and spy_date.month == current_date.month:
                    spy_ret = spy_returns[spy_date]
                    break
        
        if spy_ret is None:
            spy_ret = 0.0
        
        results.append({
            "Date": current_date,
            "Strategy": portfolio_ret,
            "Benchmark": spy_ret
        })
    
    result_df = pd.DataFrame(results).set_index("Date")
    return result_df


# === PERFORMANCE STATS ===
def perf_stats(returns, label=""):
    """
    Compute performance statistics.
    
    Args:
        returns: Series of monthly returns.
        label: Label for the result dict.
    
    Returns:
        Dict with Label, Months, Total Return, Ann. Return, Ann. Vol, Sharpe, Max DD, Win Rate, Best/Worst.
    """
    n_months = len(returns)
    if n_months == 0:
        return None
    
    # Total return
    total_ret = ((1 + returns).prod() - 1) * 100
    
    # Annualized
    years = n_months / 12.0
    ann_ret = ((1 + returns).prod() ** (1 / years) - 1) * 100 if years > 0 else 0
    
    # Volatility
    ann_vol = returns.std() * np.sqrt(12) * 100
    
    # Sharpe (assuming 0% risk-free rate)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    
    # Max drawdown
    cum = (1 + returns).cumprod()
    running_max = cum.expanding().max()
    dd = (cum - running_max) / running_max
    max_dd = dd.min() * 100
    
    # Win rate
    win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
    
    # Best/worst
    best = returns.max() * 100
    worst = returns.min() * 100
    
    return {
        "Label": label,
        "Months": n_months,
        "Total Return (%)": total_ret,
        "Ann. Return (%)": ann_ret,
        "Ann. Vol (%)": ann_vol,
        "Sharpe Ratio": sharpe,
        "Max Drawdown (%)": max_dd,
        "Win Rate (%)": win_rate,
        "Best Month (%)": best,
        "Worst Month (%)": worst
    }


# === TAX ANALYSIS ===
def apply_tax_impact(bt, holding_months=1, starting_capital=10_000):
    """
    Apply tax impact with annual netting and loss carry-forward.
    
    Args:
        bt: DataFrame from run_backtest() with Strategy and Benchmark columns.
        holding_months: Holding period (determines tax rate).
        starting_capital: Initial investment.
    
    Returns:
        Dict keyed by column name with tax details and _yearly_detail list.
    """
    tax_rate = SHORT_TERM_TAX_RATE if holding_months < 12 else LONG_TERM_TAX_RATE
    
    result = {}
    
    for col in ["Strategy", "Benchmark"]:
        if col not in bt.columns:
            continue
        
        returns = bt[col]
        balance = starting_capital
        loss_cf = 0.0  # Loss carry-forward
        yearly_detail = []
        
        # Group by year
        returns_by_year = returns.groupby(returns.index.year)
        
        for year, year_returns in returns_by_year:
            balance_start = balance
            
            # Grow balance through the year
            for monthly_ret in year_returns:
                balance *= (1 + monthly_ret)
            
            # Year-end calculations
            net_gain = balance - balance_start
            taxable_gain = max(0, net_gain - loss_cf)
            
            if taxable_gain > 0:
                tax_paid = taxable_gain * tax_rate
                balance -= tax_paid
                loss_cf_remaining = 0.0
            else:
                tax_paid = 0.0
                loss_cf_remaining = abs(net_gain - loss_cf)
            
            yearly_detail.append({
                "Year": year,
                "Net Gain": net_gain,
                "Loss C/F Used": min(loss_cf, max(0, net_gain)),
                "Taxable Gain": taxable_gain,
                "Tax Paid": tax_paid,
                "Loss C/F Remaining": loss_cf_remaining
            })
            
            loss_cf = loss_cf_remaining
        
        # Compute final metrics
        final_pre_tax = starting_capital * ((1 + returns).prod())
        pre_tax_gain = final_pre_tax - starting_capital
        pre_tax_years = len(returns_by_year)
        ann_pre_tax = ((1 + returns).prod() ** (12.0 / len(returns)) - 1) * 100 if len(returns) > 0 else 0
        
        final_after_tax = balance
        after_tax_gain = final_after_tax - starting_capital
        ann_after_tax = ((final_after_tax / starting_capital) ** (12.0 / len(returns)) - 1) * 100 if len(returns) > 0 else 0
        
        total_tax_paid = sum(yd["Tax Paid"] for yd in yearly_detail)
        tax_drag = ann_pre_tax - ann_after_tax
        
        result[col] = {
            "Starting Capital": starting_capital,
            "Final Pre-Tax": final_pre_tax,
            "Pre-Tax Gain": pre_tax_gain,
            "Ann. Pre-Tax Return": ann_pre_tax,
            "Tax Rate": tax_rate,
            "Total Tax Paid": total_tax_paid,
            "Final After-Tax": final_after_tax,
            "After-Tax Gain": after_tax_gain,
            "Ann. After-Tax Return": ann_after_tax,
            "Tax Drag (pp)": tax_drag,
            "Loss C/F Remaining": loss_cf,
            "_yearly_detail": yearly_detail
        }
    
    return result


def report_tax_impact(bt, holding_months=1, starting_capital=10_000):
    """Print formatted tax impact report."""
    tax_data = apply_tax_impact(bt, holding_months, starting_capital)
    
    _header("TAX IMPACT ANALYSIS")
    
    # Summary table
    data = []
    for col in ["Strategy", "Benchmark"]:
        if col not in tax_data:
            continue
        t = tax_data[col]
        data.append({
            "Category": col,
            "Pre-Tax Final": f"${t['Final Pre-Tax']:,.0f}",
            "Pre-Tax Ann (%)": f"{t['Ann. Pre-Tax Return']:.2f}",
            "Tax Paid": f"${t['Total Tax Paid']:,.0f}",
            "After-Tax Final": f"${t['Final After-Tax']:,.0f}",
            "After-Tax Ann (%)": f"{t['Ann. After-Tax Return']:.2f}",
            "Drag (pp)": f"{t['Tax Drag (pp)']:.2f}"
        })
    
    summary_df = pd.DataFrame(data)
    print(summary_df.to_string(index=False))
    
    # Summary line
    strat = tax_data.get("Strategy")
    if strat:
        print(f"\nStrategy: ${starting_capital:,} -> ${strat['Final Pre-Tax']:,.0f} pre-tax -> ${strat['Final After-Tax']:,.0f} after-tax")
    
    # Totals
    total_tax = sum(tax_data[col]["Total Tax Paid"] for col in ["Strategy", "Benchmark"] if col in tax_data)
    loss_cf_remaining = tax_data.get("Strategy", {}).get("Loss C/F Remaining", 0)
    print(f"\nTotal Taxes Paid: ${total_tax:,.0f}")
    if loss_cf_remaining > 0:
        print(f"Remaining Loss Carry-Forward: ${loss_cf_remaining:,.0f}")
    
    # Yearly detail for Strategy
    if "Strategy" in tax_data:
        _header("STRATEGY - YEARLY TAX BREAKDOWN")
        yearly = tax_data["Strategy"]["_yearly_detail"]
        yearly_df = pd.DataFrame(yearly)
        annual_cols = ["Year", "Net Gain", "Loss C/F Used", "Taxable Gain", "Tax Paid", "Loss C/F Remaining"]
        for col in annual_cols:
            if col in ["Net Gain", "Loss C/F Used", "Taxable Gain", "Tax Paid", "Loss C/F Remaining"]:
                yearly_df[col] = yearly_df[col].apply(lambda x: f"${x:,.0f}")
        print(yearly_df[annual_cols].to_string(index=False))


# === REPORTING ===
def report_current_picks(picks, info, lookback, skip):
    """Print current picks with momentum and sector allocation."""
    _header("CURRENT PICKS")
    
    # Signal description
    print(f"Signal: 6-month momentum (lookback={lookback}, skip={skip})")
    print(f"Weighting: Inverse volatility")
    print(f"Universe: {len(info)} stocks")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    # Merge with info (picks should already have Ticker as a column)
    info_reset = info.reset_index()
    picks = picks.merge(info_reset, on="Ticker", how="left")
    
    # Display table
    display_cols = ["Company", "Sector", "Momentum (%)", "Monthly Vol (%)", "Ann. Vol (%)", "Weight (%)"]
    display_df = picks[display_cols].copy()
    for col in ["Momentum (%)", "Monthly Vol (%)", "Ann. Vol (%)", "Weight (%)"]:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}")
    
    print(display_df.to_string(index=False))
    print()
    
    # Sector allocation
    print("Sector Allocation:")
    sector_weights = picks.groupby("Sector")["Weight (%)"].sum().sort_values(ascending=False)
    for sector, weight in sector_weights.items():
        bars = int(weight / 2)
        bar_char = '█'
        try:
            # Test if the character can be encoded
            bar_char.encode('cp1252')
        except UnicodeEncodeError:
            # Fall back to # if block character doesn't work
            bar_char = '#'
        print(f"  {sector:30s} {weight:6.2f}% {bar_char * bars}")


def _compare_picks(current, previous):
    """Compare current picks with previous run."""
    if previous is None:
        print("No previous picks to compare.")
        return
    
    print()
    _header("PORTFOLIO COMPARISON")
    
    current_set = set(current["Ticker"])
    previous_set = set(previous["Ticker"])
    
    kept = current_set & previous_set
    new = current_set - previous_set
    dropped = previous_set - current_set
    turnover = (len(new) + len(dropped)) / len(previous_set) * 100 if len(previous_set) > 0 else 0
    
    print(f"Stocks kept: {len(kept)}")
    print(f"New entries: {len(new)}")
    print(f"Dropped: {len(dropped)}")
    print(f"Turnover: {turnover:.1f}%")
    
    # New entries
    if len(new) > 0:
        print("\nNew Entries:")
        new_picks = current[current["Ticker"].isin(new)].sort_values("Momentum (%)", ascending=False)
        for _, row in new_picks.iterrows():
            print(f"  {row['Ticker']:6s} {row['Momentum (%)']:7.2f}% momentum, {row['Weight (%)']:5.2f}% weight")
    
    # Dropped
    if len(dropped) > 0:
        print("\nDropped Tickers:")
        print(f"  {', '.join(sorted(dropped))}")
    
    # Weight changes
    if len(kept) > 0:
        kept_current = current[current["Ticker"].isin(kept)].set_index("Ticker")
        kept_previous = previous[previous["Ticker"].isin(kept)].set_index("Ticker")
        kept_current = kept_current.loc[kept_current.index.isin(kept_previous.index)]
        kept_previous = kept_previous.loc[kept_previous.index.isin(kept_current.index)]
        
        weight_changes = (kept_current["Weight (%)"] - kept_previous["Weight (%)"]).abs()
        weight_changes = weight_changes[weight_changes >= 0.5].sort_values(ascending=False).head(10)
        
        if len(weight_changes) > 0:
            print("\nWeight Changes (>=0.5pp, top 10):")
            for ticker, change in weight_changes.items():
                direction = "+" if kept_current.loc[ticker, "Weight (%)"] > kept_previous.loc[ticker, "Weight (%)"] else "-"
                print(f"  {ticker:6s} {direction}{change:.2f}pp")


def _save_picks_csv(picks, info, args, monthly_returns):
    """Save picks to CSV with metadata."""
    _ensure_cache_dir()
    
    # Merge with info
    picks = picks.reset_index()
    picks = picks.merge(info.reset_index(), on="Ticker", how="left")
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_path = CACHE_DIR / f"picks_{timestamp}.csv"
    
    # Metadata
    metadata = [
        f"# Signal: {args.lookback}-month momentum (skip={args.skip})",
        f"# Date: {timestamp}",
        f"# Universe: {len(info)} stocks",
        f"# Top N: {args.top_n}",
        f"# Min Market Cap: {args.min_cap}B" if args.min_cap else "# Min Market Cap: None",
        f"# Price Data Range: {monthly_returns.index[0].strftime('%Y-%m-%d')} to {monthly_returns.index[-1].strftime('%Y-%m-%d')}"
    ]
    
    # Write with metadata
    with open(output_path, "w", newline="") as f:
        f.write("\n".join(metadata) + "\n")
        picks.to_csv(f, index=False)
    
    print(f"Picks saved to: {output_path}")
    
    # Copy to custom output if specified
    if args.output:
        output_custom = Path(args.output)
        with open(output_path, "r") as src:
            with open(output_custom, "w") as dst:
                dst.write(src.read())
        print(f"Also saved to: {output_custom}")


def report_backtest(bt, lookback, skip, top_n):
    """Print backtest results and save equity curve."""
    _header("BACKTEST RESULTS")
    
    # Statistics
    strat_stats = perf_stats(bt["Strategy"], label="Strategy")
    bench_stats = perf_stats(bt["Benchmark"], label="Benchmark")
    
    print("Summary Statistics:")
    stats_data = []
    for key in ["Months", "Total Return (%)", "Ann. Return (%)", "Ann. Vol (%)", "Sharpe Ratio", "Max Drawdown (%)", "Win Rate (%)"]:
        row = {
            "Metric": key,
            "Strategy": f"{strat_stats[key]:.2f}" if isinstance(strat_stats[key], float) else strat_stats[key],
            "Benchmark": f"{bench_stats[key]:.2f}" if isinstance(bench_stats[key], float) else bench_stats[key]
        }
        stats_data.append(row)
    
    stats_df = pd.DataFrame(stats_data)
    print(stats_df.to_string(index=False))
    
    # Growth of $10k
    print(f"\nGrowth of $10,000:")
    strat_final = 10_000 * ((1 + bt["Strategy"]).prod())
    bench_final = 10_000 * ((1 + bt["Benchmark"]).prod())
    print(f"  Strategy:  ${strat_final:,.0f}")
    print(f"  Benchmark: ${bench_final:,.0f}")
    
    # Annual returns table
    print("\nAnnual Returns:")
    annual_returns = bt.groupby(bt.index.year).apply(lambda x: {
        "Year": x.index[0].year,
        "Strategy (%)": ((1 + x["Strategy"]).prod() - 1) * 100,
        "Benchmark (%)": ((1 + x["Benchmark"]).prod() - 1) * 100,
    })
    
    # Compute year-end values
    annual_list = []
    strat_val = 10_000
    bench_val = 10_000
    for year in sorted(bt.index.year.unique()):
        year_data = bt[bt.index.year == year]
        strat_ret = ((1 + year_data["Strategy"]).prod() - 1) * 100
        bench_ret = ((1 + year_data["Benchmark"]).prod() - 1) * 100
        strat_val *= (1 + year_data["Strategy"].prod())
        bench_val *= (1 + year_data["Benchmark"].prod())
        excess_ret = strat_ret - bench_ret
        
        annual_list.append({
            "Year": year,
            "Strategy (%)": f"{strat_ret:.2f}",
            "Strat Value ($)": f"{strat_val:,.0f}",
            "Benchmark (%)": f"{bench_ret:.2f}",
            "Bench Value ($)": f"{bench_val:,.0f}",
            "Excess (%)": f"{excess_ret:.2f}"
        })
    
    annual_df = pd.DataFrame(annual_list)
    print(annual_df.to_string(index=False))
    
    # Save equity curve
    equity_curve = 10_000 * ((1 + bt).cumprod())
    equity_curve.to_csv(CACHE_DIR / "backtest_equity_curve.csv")
    print(f"\nEquity curve saved to: {CACHE_DIR / 'backtest_equity_curve.csv'}")


# === MAIN ===
def main():
    """Main flow."""
    parser = argparse.ArgumentParser(
        description="S&P 500 Momentum Stock-Picking Strategy"
    )
    parser.add_argument("--top-n", type=int, default=20, help="Number of stocks to select")
    parser.add_argument("--lookback", type=int, default=6, help="Momentum lookback in months")
    parser.add_argument("--skip", type=int, default=1, help="Recent months to skip")
    parser.add_argument("--years", type=int, default=5, help="Years of price history for backtest")
    parser.add_argument("--min-cap", type=float, default=None, help="Min market cap in $B")
    parser.add_argument("--output", type=str, default=None, help="Copy picks CSV to custom path")
    parser.add_argument("--no-backtest", action="store_true", help="Skip backtest")
    parser.add_argument("--apply-tax", action="store_true", help="Show after-tax analysis")
    parser.add_argument("--refresh", action="store_true", help="Force re-download prices")
    
    args = parser.parse_args()
    
    # Step 1: Fetch S&P 500 constituents
    print("Fetching S&P 500 constituents...")
    info = get_sp500_info()
    print(f"  {len(info)} stocks")
    
    # Step 2: Load tickers and prices
    tickers = list(info.index)
    
    # Add SPY benchmark
    if "SPY" not in tickers:
        tickers = tickers + ["SPY"]
    
    print(f"Downloading {len(tickers)} tickers...")
    prices = fetch_monthly_prices(tickers, years=args.years, refresh=args.refresh)
    
    # Filter to only tickers with data
    if len(prices) > 0:
        prices = prices.dropna(axis=1, how='all')  # Drop columns that are all NaN
    
    if len(prices) == 0 or prices.shape[0] == 0:
        print("Error: No price data retrieved. This may be a network issue.")
        sys.exit(1)
    
    # Separate SPY from stocks
    if "SPY" in prices.columns:
        spy_prices = prices["SPY"]
        stock_prices = prices.drop(columns=["SPY"])
    else:
        # SPY wasn't in the download, get it separately
        print("Downloading SPY separately...")
        try:
            if len(prices) > 0:
                start_date = prices.index[0]
            else:
                start_date = (datetime.now() - timedelta(days=args.years * 365 + 210)).strftime("%Y-%m-%d")
            
            spy_data = yf.download("SPY", start=start_date, interval="1mo", progress=False)
            if isinstance(spy_data, pd.DataFrame):
                spy_prices = spy_data["Adj Close"]
            else:
                spy_prices = spy_data
        except Exception as e:
            print(f"Failed to download SPY: {e}")
            sys.exit(1)
        
        stock_prices = prices
    
    # Ensure stock prices has tickers from S&P 500
    stock_prices = stock_prices[[t for t in info.index if t in stock_prices.columns]]
    
    # Step 3: Apply market cap filter if needed
    if args.min_cap is not None:
        cached = _load_tickers_from_cache()
        if cached is not None and "Market Cap ($B)" in cached.columns:
            valid_tickers = cached[cached["Market Cap ($B)"] >= args.min_cap]["Ticker"].tolist()
            stock_prices = stock_prices[[t for t in valid_tickers if t in stock_prices.columns]]
            info = info.loc[info.index.isin(stock_prices.columns)]
            print(f"Applied market cap filter: {len(info)} stocks remain")
        else:
            print("Warning: Market cap data not available in cache")
    
    # Step 4: Score and select
    monthly_returns = stock_prices.pct_change()
    scores = momentum_scores(monthly_returns, lookback=args.lookback, skip=args.skip)
    picks = select_top(scores, top_n=args.top_n)
    
    # Step 5: Report current picks
    picks_for_report = picks.reset_index()  # Make Ticker a column for reporting
    report_current_picks(picks_for_report, info, args.lookback, args.skip)
    
    # Step 6: Compare with previous
    previous = _load_previous_picks()
    _compare_picks(picks_for_report, previous)
    
    # Step 7: Save picks
    _save_picks_csv(picks_for_report, info, args, stock_prices)
    
    # Step 8: Backtest
    if not args.no_backtest:
        print("\nRunning backtest...")
        spy_returns = spy_prices.pct_change()
        bt = run_backtest(monthly_returns, spy_returns, lookback=args.lookback, skip=args.skip, top_n=args.top_n)
        
        if len(bt) > 0:
            report_backtest(bt, args.lookback, args.skip, args.top_n)
            
            # Step 9: Tax analysis
            if args.apply_tax:
                report_tax_impact(bt, holding_months=1, starting_capital=10_000)
        else:
            print("No backtest results (insufficient data).")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
