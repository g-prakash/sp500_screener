import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pytz
from datetime import datetime
from pathlib import Path

# === CONSTANTS ===
SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / "sp500_cache"
PICKS_FILE = CACHE_DIR / "picks_2026-03-03.csv"
START_DATE = "2026-03-03"
END_DATE = (datetime.now() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")  # Dynamic: tomorrow's date
INITIAL_INVESTMENT = 10000
INTERVAL = "30m" 

def load_picks():
    """Load the picks CSV file."""
    if not PICKS_FILE.exists():
        raise FileNotFoundError(f"Picks file not found: {PICKS_FILE}")
    
    df = pd.read_csv(PICKS_FILE, comment='#')
    print(f"Loaded {len(df)} picks from {PICKS_FILE.name}")
    return df

def download_price_data(tickers, start_date, end_date):
    """Download 30-minute interval price data."""
    print(f"\nDownloading {INTERVAL} data from {start_date} to {end_date}...")
    data = yf.download(tickers, start=start_date, end=end_date, interval=INTERVAL, progress=False, threads=True)
    
    if data.empty:
        raise ValueError("No data found for the given range and interval.")

    # Extract Close prices
    if isinstance(data.columns, pd.MultiIndex):
        adj_close = data.xs('Close', level=0, axis=1)
    else:
        adj_close = data[['Close']].copy()
        adj_close.columns = [tickers[0] if isinstance(tickers, list) else tickers]
    
    # Handle missing values (e.g. stock-specific halts)
    adj_close = adj_close.ffill().bfill()
    
    print(f"Downloaded {len(adj_close)} intervals for {len(adj_close.columns)} tickers")
    return adj_close

def calculate_returns(price_data):
    """Calculate interval returns from price data."""
    # Using fillna(0) for the first row ensures the portfolio starts at 1.0 multiplier
    returns = price_data.pct_change().fillna(0)
    return returns

def calculate_portfolio_returns(returns, weights):
    """Calculate weighted portfolio returns."""
    weight_values = list(weights.values())
    total_weight = sum(weight_values)
    normalized_weights = {ticker: w / total_weight for ticker, w in weights.items()}
    
    available_tickers = [t for t in returns.columns if t in normalized_weights]
    filtered_returns = returns[available_tickers]
    
    portfolio_returns = filtered_returns.mul(
        pd.Series({t: normalized_weights[t] for t in available_tickers}),
        axis=1
    ).sum(axis=1)
    
    return portfolio_returns

def calculate_portfolio(price_data, weights_dict):
    """Calculates the portfolio growth series."""
    # Only use tickers that actually exist in the downloaded data
    available_tickers = [t for t in weights_dict.keys() if t in price_data.columns]
    
    # Re-normalize weights for available tickers
    sub_weights = {t: weights_dict[t] for t in available_tickers}
    total_w = sum(sub_weights.values())
    norm_weights = {t: w / total_w for t, w in sub_weights.items()}
    
    # Calculate returns
    returns = price_data[available_tickers].pct_change().fillna(0)
    
    # Calculate weighted daily returns
    portfolio_returns = (returns * pd.Series(norm_weights)).sum(axis=1)
    
    # Calculate cumulative value
    portfolio_value_series = INITIAL_INVESTMENT * (1 + portfolio_returns).cumprod()
    return portfolio_value_series

def plot_portfolio_performance(df, starting_fund, save_path, spy_df=None):
    """
    Plot an intraday portfolio index chart with gap elimination and optional SPY overlay.
    
    Parameters:
    -----------
    df : DataFrame with DatetimeIndex (UTC) and "Index Value ($)" column
    starting_fund : float (e.g., 10000)
    save_path : Path to save the PNG
    spy_df : optional DataFrame with same structure for SPY benchmark overlay
    """
    import matplotlib.patches as mpatches
    
    # 1. TIMEZONE CONVERSION: UTC to America/New_York
    if df.index.tz is None:
        df_et = df.copy()
        df_et.index = df.index.tz_localize('UTC')
    else:
        df_et = df.copy()
    df_et.index = df_et.index.tz_convert('America/New_York')
    
    # Handle spy_df if provided
    if spy_df is not None:
        if spy_df.index.tz is None:
            spy_et = spy_df.copy()
            spy_et.index = spy_et.index.tz_localize('UTC')
        else:
            spy_et = spy_df.copy()
        spy_et.index = spy_et.index.tz_convert('America/New_York')
        # Forward-fill align SPY to portfolio timestamps
        spy_et = spy_et.reindex(df_et.index, method='ffill')
    
    # 2. GAP ELIMINATION: Create sequential x-axis
    x_data = range(len(df_et))
    portfolio_values = df_et['Index Value ($)'].values
    spy_values = spy_et['Index Value ($)'].values if spy_df is not None else None
    timestamps = df_et.index
    
    # 3. CALCULATE RETURNS
    portfolio_return = (portfolio_values[-1] - starting_fund) / starting_fund * 100
    spy_return = (spy_values[-1] - starting_fund) / starting_fund * 100 if spy_df is not None else None
    
    # 4. CREATE FIGURE
    fig, ax = plt.subplots(figsize=(14, 6), dpi=150)
    
    # 5. PLOT PORTFOLIO LINE
    ax.plot(x_data, portfolio_values, color='#1f77b4', linewidth=1.2, 
            label=f'Portfolio ({portfolio_return:+.2f}%)', zorder=2)
    
    # 6. PLOT SPY OVERLAY if provided
    if spy_df is not None:
        ax.plot(x_data, spy_values, color='#ff7f0e', linewidth=1.2,
                label=f'SPY ({spy_return:+.2f}%)', zorder=2)
    
    # 7. STARTING FUND REFERENCE LINE
    ax.axhline(y=starting_fund, color='gray', linestyle='--', alpha=0.7, linewidth=1, 
               label=f'Starting ${starting_fund:,.0f}', zorder=1)
    
    # 8. DAY-BOUNDARY VERTICAL LINES
    for i in range(1, len(timestamps)):
        if timestamps[i].date() != timestamps[i-1].date():
            ax.axvline(x=i - 0.5, color='gray', linestyle='--', alpha=0.4, linewidth=0.5, zorder=0)
    
    # 9. GRID
    ax.grid(True, which='major', alpha=0.3, zorder=0)
    ax.grid(True, which='minor', alpha=0.15, linestyle=':', zorder=0)
    
    # 10. X-AXIS TICKS: Only at whole hours 10:00, 12:00, 14:00, 16:00
    tick_positions = []
    tick_labels = []
    last_date = None
    
    for i, ts in enumerate(timestamps):
        if ts.hour in [10, 12, 14, 16] and ts.minute == 0:
            tick_positions.append(i)
            # Check if it's a new date
            if last_date != ts.date():
                label = ts.strftime('%b %d\n%H:%M')
                last_date = ts.date()
            else:
                label = ts.strftime('%H:%M')
            tick_labels.append(label)
    
    ax.set_xticks(tick_positions, tick_labels, fontsize=8, rotation=90, ha='center')
    
    # 11. X-AXIS LIMITS with padding
    ax.set_xlim(-0.5, len(x_data) - 0.5)
    
    # 12. TITLES AND LABELS
    ax.set_title('Momentum Portfolio vs SPY — Index Value', fontsize=14, fontweight='bold')
    ax.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax.set_xlabel('Date / Time (ET)', fontsize=12)
    
    # 13. LEGEND
    ax.legend(loc='upper left', frameon=True, shadow=True)
    
    # 14. ANNOTATIONS: Latest portfolio value
    ax.annotate(f'${portfolio_values[-1]:,.0f}',
                xy=(len(x_data) - 1, portfolio_values[-1]),
                xytext=(10, 10), textcoords='offset points',
                color='#1f77b4', fontweight='bold', fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#d6eaf8', alpha=0.8, edgecolor='none'),
                arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=1.5),
                zorder=3)
    
    # 15. ANNOTATIONS: Latest SPY value (if present)
    if spy_df is not None:
        ax.annotate(f'${spy_values[-1]:,.0f}',
                    xy=(len(x_data) - 1, spy_values[-1]),
                    xytext=(10, -20), textcoords='offset points',
                    color='#ff7f0e', fontweight='bold', fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#fdebd0', alpha=0.8, edgecolor='none'),
                    arrowprops=dict(arrowstyle='->', color='#ff7f0e', lw=1.5),
                    zorder=3)
    
    # 16. SAVE AND SHOW
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    print(f"Chart saved to {save_path}")
    plt.show()

def main():
    # 1. Load Data
    try:
        picks_df = load_picks()
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    tickers = picks_df['Ticker'].tolist()
    weights = dict(zip(picks_df['Ticker'], picks_df['Weight (%)']))
    
    # 2. Get Prices
    price_data = download_price_data(tickers, START_DATE, END_DATE)
    
    # 3. Download SPY for reference
    print(f"\nDownloading SPY reference data from {START_DATE} to {END_DATE}...")
    spy_data = yf.download('SPY', start=START_DATE, end=END_DATE, interval=INTERVAL, progress=False)
    
    # Handle both Series and DataFrame returns from yfinance
    if isinstance(spy_data, pd.DataFrame):
        spy_close = spy_data['Close']
    else:
        spy_close = spy_data
    
    # Ensure it's a Series, not a DataFrame
    if isinstance(spy_close, pd.DataFrame):
        spy_close = spy_close.squeeze()
    
    spy_returns = spy_close.pct_change().fillna(0)
    spy_value = INITIAL_INVESTMENT * (1 + spy_returns).cumprod()
    
    # 4. Calculate Portfolio
    portfolio_series = calculate_portfolio(price_data, weights)
    
    # 5. Create DataFrames with "Index Value ($)" column for the new plot function
    portfolio_df = pd.DataFrame(index=portfolio_series.index)
    portfolio_df['Index Value ($)'] = portfolio_series.values
    
    spy_df = pd.DataFrame(index=spy_value.index)
    spy_df['Index Value ($)'] = spy_value.values if isinstance(spy_value, pd.Series) else spy_value
    
    # 6. Save results to CSV
    picks_filename = PICKS_FILE.stem  # Extract filename without extension (e.g., "picks_2026-03-03")
    output_csv = SCRIPT_DIR / f"hourly_index_{picks_filename}.csv"
    
    # Create combined results DataFrame for CSV export
    results = pd.DataFrame(index=portfolio_series.index)
    results['Portfolio Value'] = portfolio_series.values
    results['SPY Value'] = spy_value.values
    results.to_csv(output_csv)
    print(f"\nResults saved to {output_csv.name}")
    
    # 7. Output summary
    portfolio_final = float(portfolio_series.iloc[-1].item() if hasattr(portfolio_series.iloc[-1], 'item') else portfolio_series.iloc[-1])
    spy_final = float(spy_value.iloc[-1].item() if hasattr(spy_value.iloc[-1], 'item') else spy_value.iloc[-1])
    portfolio_return = (portfolio_final - INITIAL_INVESTMENT) / INITIAL_INVESTMENT * 100
    spy_return = (spy_final - INITIAL_INVESTMENT) / INITIAL_INVESTMENT * 100
    
    print("\n" + "="*45)
    print(f"Start Value: ${INITIAL_INVESTMENT:,.2f}")
    print(f"Portfolio Final Value: ${portfolio_final:,.2f} ({portfolio_return:+.2f}%)")
    print(f"SPY Final Value: ${spy_final:,.2f} ({spy_return:+.2f}%)")
    print(f"Current ET Time: {portfolio_series.index[-1]}")
    print("="*45)
    
    # 8. Plot Portfolio Performance
    chart_path = SCRIPT_DIR / "portfolio_chart_fixed.png"
    plot_portfolio_performance(portfolio_df, INITIAL_INVESTMENT, chart_path, spy_df)

if __name__ == "__main__":
    main()