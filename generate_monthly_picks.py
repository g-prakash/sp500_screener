#!/usr/bin/env python3
"""
Generate monthly S&P 500 momentum-based stock picks for the first day of each month (last 6 months).
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta

# === CONSTANTS ===
SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "sp500_cache"
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

CACHE_DIR.mkdir(exist_ok=True)

# === GET S&P 500 CONSTITUENTS ===
def get_sp500_info():
    """Fetch or load cached S&P 500 companies."""
    # Try to load from cache first
    cache_files = sorted(CACHE_DIR.glob("sp500_all_*.csv"), reverse=True)
    if cache_files:
        try:
            df = pd.read_csv(cache_files[0])
            df = df.set_index("Ticker")
            print(f"  Loaded {len(df)} tickers from cache: {cache_files[0].name}")
            return df
        except Exception as e:
            print(f"  Warning: Could not load cache: {e}")
    
    # Fall back to Wikipedia
    try:
        print("  Fetching from Wikipedia...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(WIKIPEDIA_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        
        tables = pd.read_html(resp.text)
        df = tables[0]
        
        # Normalize columns
        df.columns = [col.strip() for col in df.columns]
        
        if "Symbol" in df.columns:
            df["Ticker"] = df["Symbol"].str.replace(r"\[.*\]", "", regex=True)
        elif "Ticker" not in df.columns:
            raise ValueError("Could not find ticker column")
        
        df = df.set_index("Ticker")
        print(f"  Loaded {len(df)} tickers from Wikipedia")
        return df
    except Exception as e:
        print(f"ERROR: Could not fetch S&P 500 data: {e}")
        return None

# === GET MONTHLY PRICES ===
def get_monthly_prices(tickers, end_date, lookback_months=12):
    """Get monthly prices up to end_date."""
    start_date = end_date - relativedelta(months=lookback_months)
    
    print(f"  Downloading from {start_date.date()} to {end_date.date()}...")
    
    try:
        prices = yf.download(
            tickers,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1mo",
            threads=True,
            progress=False
        )
        
        # Handle MultiIndex
        if isinstance(prices.columns, pd.MultiIndex):
            if "Adj Close" in prices.columns.get_level_values(0):
                prices = prices.xs("Adj Close", level=0, axis=1)
            elif "Close" in prices.columns.get_level_values(0):
                prices = prices.xs("Close", level=0, axis=1)
        
        # Drop incomplete/NaN rows
        prices = prices.dropna(how="all")
        
        return prices
    except Exception as e:
        print(f"  Error downloading prices: {e}")
        return None

# === MOMENTUM SCORING ===
def momentum_scores(monthly_returns, lookback=6, skip=1):
    """Calculate momentum scores."""
    window = monthly_returns.iloc[-(lookback + skip):-skip]
    
    momentum = ((1 + window).prod() - 1) * 100
    vol_monthly = window.std() * 100
    vol_annual = vol_monthly * np.sqrt(12)
    
    result = pd.DataFrame({
        "Momentum (%)": momentum,
        "Monthly Vol (%)": vol_monthly,
        "Ann. Vol (%)": vol_annual
    })
    
    return result.dropna()

# === SELECT TOP STOCKS ===
def select_top(scores, top_n=10):
    """Select top N stocks by momentum, weight by inverse volatility."""
    top = scores.nlargest(top_n, "Momentum (%)")
    
    vol = top["Ann. Vol (%)"]
    inv_vol = 1.0 / vol
    weights = (inv_vol / inv_vol.sum()) * 100
    
    top = top.copy()
    top["Weight (%)"] = weights
    
    return top

# === MAIN ===
def main():
    print("\n" + "="*60)
    print("GENERATING MONTHLY PICKS FOR LAST 6 MONTHS (FIRST DAY)")
    print("="*60)
    
    # Get S&P 500 constituents
    print("\n[1] Fetching S&P 500 constituents...")
    sp500_info = get_sp500_info()
    if sp500_info is None:
        print("ERROR: Could not fetch S&P 500 data")
        return
    
    tickers = sp500_info.index.tolist()
    print(f"  Found {len(tickers)} tickers")
    
    # Generate picks for first day of each month (last 6 months)
    picks_generated = []
    today = datetime.now()
    
    for i in range(6):
        # Calculate first day of the month, going back i months
        month_date = today - relativedelta(months=i)
        first_day = month_date.replace(day=1)
        
        date_str = first_day.strftime("%Y-%m-%d")
        print(f"\n[{i+2}] Processing: {date_str}")
        
        try:
            # Get monthly prices up to first day of month
            prices = get_monthly_prices(tickers, first_day, lookback_months=12)
            
            if prices is None or len(prices) < 7:
                print(f"  ⚠ Not enough data (got {len(prices) if prices is not None else 0} months)")
                continue
            
            print(f"  Downloaded {len(prices)} months of data for {len(prices.columns)} tickers")
            
            # Calculate returns
            returns = prices.pct_change()
            
            # Calculate momentum scores
            scores = momentum_scores(returns, lookback=6, skip=1)
            
            if len(scores) == 0:
                print(f"  ⚠ No valid scores calculated")
                continue
            
            print(f"  Calculated scores for {len(scores)} tickers")
            
            # Select top 10
            picks = select_top(scores, top_n=10)
            
            # Merge with company info
            picks_with_info = picks.reset_index()
            picks_with_info = picks_with_info.merge(
                sp500_info.reset_index(),
                on="Ticker",
                how="left"
            )
            
            # Rename columns
            picks_with_info = picks_with_info.rename(columns={
                "Security": "Company",
                "GICS Sector": "Sector",
                "GICS Sub-Industry": "Industry"
            })
            
            # Save to CSV
            output_file = CACHE_DIR / f"picks_{date_str}.csv"
            picks_with_info.to_csv(output_file, index=False)
            
            print(f"  ✓ Saved {len(picks_with_info)} picks to {output_file.name}")
            print(f"    Top pick: {picks.index[0]} ({picks['Momentum (%)'].iloc[0]:+.2f}% momentum, weight {picks['Weight (%)'].iloc[0]:.1f}%)")
            
            picks_generated.append(date_str)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print("\n" + "="*60)
    print(f"GENERATED {len(picks_generated)} MONTHLY PICKS")
    print("="*60)
    for date_str in reversed(picks_generated):
        print(f"  • {date_str}")
    
    print(f"\nAll picks saved to: {CACHE_DIR}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
