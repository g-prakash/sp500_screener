import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path
import numpy as np

# === CONSTANTS ===
SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "sp500_cache"
PICKS_FILE = CACHE_DIR / "picks_2026-03-03.csv"
START_DATE = "2026-03-03"
INITIAL_INVESTMENT = 10000
INTERVAL = "30m"  # Updated to 30 minutes


def load_picks():
    """Load the picks CSV file."""
    if not PICKS_FILE.exists():
        # Fallback for demonstration if directory structure is different
        raise FileNotFoundError(f"Picks file not found: {PICKS_FILE}")
    
    df = pd.read_csv(PICKS_FILE, comment='#')
    print(f"Loaded {len(df)} picks from {PICKS_FILE.name}")
    print(df[['Ticker', 'Weight (%)']].to_string(index=False))
    return df


def download_price_data(tickers, start_date):
    """Download 30-minute price data for all tickers."""
    print(f"\nDownloading {INTERVAL} price data from {start_date}...")
    # interval="30m" provides intraday data
    data = yf.download(tickers, start=start_date, interval=INTERVAL, progress=False)
    
    if data.empty:
        raise ValueError("No data downloaded. Check if the date range is within the last 60 days for 30m data.")

    # Extract Close prices
    if isinstance(data.columns, pd.MultiIndex):
        adj_close = data.xs('Close', level=0, axis=1)
    else:
        adj_close = data[['Close']].copy()
        adj_close.columns = [tickers[0] if isinstance(tickers, list) else tickers]
    
    # Forward fill missing values to handle symbols that might not trade every 30m
    adj_close = adj_close.ffill()
    
    print(f"Downloaded {len(adj_close)} data points for {len(adj_close.columns)} tickers")
    return adj_close


def calculate_returns(price_data):
    """Calculate interval returns from price data."""
    # We use fillna(0) for the first row to ensure we keep the starting timestamp
    returns = price_data.pct_change().fillna(0)
    return returns


def calculate_portfolio_returns(returns, weights):
    """Calculate weighted portfolio returns for the given intervals."""
    # Normalize weights to sum to 1.0
    weight_values = list(weights.values())
    total_weight = sum(weight_values)
    normalized_weights = {ticker: w / total_weight for ticker, w in weights.items()}
    
    # Filter returns to only include tickers available in the data
    available_tickers = [t for t in returns.columns if t in normalized_weights]
    
    # Calculate weighted returns
    filtered_returns = returns[available_tickers]
    portfolio_returns = filtered_returns.mul(
        pd.Series({t: normalized_weights[t] for t in available_tickers}),
        axis=1
    ).sum(axis=1)
    
    return portfolio_returns


def calculate_portfolio_value(portfolio_returns, initial_investment):
    """Calculate cumulative portfolio value starting from initial investment."""
    # (1 + r).cumprod() gives the growth multiplier over time
    cumulative_growth = (1 + portfolio_returns).cumprod()
    portfolio_value = initial_investment * cumulative_growth
    return portfolio_value


def main():
    # Load picks
    try:
        picks_df = load_picks()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    tickers = picks_df['Ticker'].tolist()
    weights = dict(zip(picks_df['Ticker'], picks_df['Weight (%)']))
    
    # Download price data
    price_data = download_price_data(tickers, START_DATE)
    
    # Calculate returns (using the updated function name)
    returns = calculate_returns(price_data)
    portfolio_returns = calculate_portfolio_returns(returns, weights)
    portfolio_value = calculate_portfolio_value(portfolio_returns, INITIAL_INVESTMENT)
    
    # Create results DataFrame
    results = pd.DataFrame({
        'Timestamp': portfolio_returns.index,
        'Interval Return (%)': portfolio_returns.values * 100,
        'Portfolio Value ($)': portfolio_value.values
    })
    results.set_index('Timestamp', inplace=True)
    
    # Display summary
    print("\n" + "="*70)
    print(f"PORTFOLIO RETURNS SUMMARY (Interval: {INTERVAL})")
    print("="*70)
    print(f"Initial Investment: ${INITIAL_INVESTMENT:,.2f}")
    print(f"Start Date: {START_DATE}")
    print(f"Total Intervals: {len(results)}")
    print(f"\nFinal Portfolio Value: ${results['Portfolio Value ($)'].iloc[-1]:,.2f}")
    
    total_return_pct = ((results['Portfolio Value ($)'].iloc[-1] / INITIAL_INVESTMENT) - 1) * 100
    print(f"Total Return: {total_return_pct:.2f}%")
    print(f"Avg Return per 30m: {results['Interval Return (%)'].mean():.4f}%")
    
    print("\nFirst 10 intervals (30-min):")
    print(results.head(10).to_string())
    
    print("\nLast 10 intervals (30-min):")
    print(results.tail(10).to_string())
    
    # Save results
    output_file = SCRIPT_DIR / "intraday_returns_2026-03-03.csv"
    results.to_csv(output_file)
    print(f"\nResults saved to {output_file.name}")


if __name__ == "__main__":
    main()