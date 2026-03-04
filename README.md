# S&P 500 Momentum Stock-Picking Strategy

A Python-based momentum stock-picking strategy with backtesting, tax analysis, and portfolio comparison. It identifies the top momentum stocks from the S&P 500 and evaluates their historical performance.

## Features

- **S&P 500 Constituents:** Fetches current list from Wikipedia with fallback to cached data
- **Momentum Scoring:** 6-month rolling momentum with inverse volatility weighting
- **Historical Backtesting:** Month-by-month forward walk with SPY benchmark comparison
- **Tax Analysis:** Annual loss carry-forward, short-term (35%) and long-term (20%) tax rates
- **Portfolio Tracking:** Compare current picks vs previous run, track turnover and weight changes
- **Performance Metrics:** Return, volatility, Sharpe ratio, max drawdown, win rate
- **Price Caching:** All data cached in `sp500_cache/` to avoid re-downloads

## Installation

### Requirements
- Python 3.8+
- Virtual environment (recommended)

### Setup

1. Clone or download this repository
2. Create a virtual environment:
   ```powershell
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

4. Install dependencies:
   ```powershell
   .\venv\Scripts\pip.exe install numpy pandas requests yfinance lxml
   ```

## Usage

### Basic Commands

**Default run (top 20 stocks, 5-year backtest):**
```powershell
python sp500_momentum.py
```

**Top 10 momentum stocks:**
```powershell
python sp500_momentum.py --top-n 10
```

**Top 15 with 2-year backtest:**
```powershell
python sp500_momentum.py --top-n 15 --years 2
```

**Top 10 with long backtest (10 years):**
```powershell
python sp500_momentum.py --top-n 10 --years 10
```

### Advanced Options

**Include after-tax analysis (35% short-term, 20% long-term):**
```powershell
python sp500_momentum.py --top-n 10 --apply-tax
```

**Skip backtest, picks only:**
```powershell
python sp500_momentum.py --top-n 20 --no-backtest
```

**Force re-download of price data (refresh cache):**
```powershell
python sp500_momentum.py --refresh
```

**Save picks to custom file:**
```powershell
python sp500_momentum.py --output my_picks.csv
```

**Filter by minimum market cap ($50B+):**
```powershell
python sp500_momentum.py --min-cap 50
```

### Combined Examples

**Comprehensive analysis - top 10, 3 years, after-tax, custom output:**
```powershell
python sp500_momentum.py --top-n 10 --years 3 --apply-tax --output my_analysis.csv
```

**Quick scan - top 20, skip backtest:**
```powershell
python sp500_momentum.py --top-n 20 --no-backtest
```

**Full backtest with tax impact:**
```powershell
python sp500_momentum.py --years 5 --top-n 10 --apply-tax --refresh
```

## CLI Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--top-n` | int | 20 | Number of stocks to select |
| `--lookback` | int | 6 | Momentum lookback in months |
| `--skip` | int | 1 | Recent months to skip (avoids mean-reversion) |
| `--years` | int | 5 | Years of price history for backtest |
| `--min-cap` | float | None | Min market cap in $B |
| `--output` | str | None | Copy picks CSV to custom path |
| `--no-backtest` | flag | False | Skip the backtest |
| `--apply-tax` | flag | False | Show after-tax analysis |
| `--refresh` | flag | False | Force re-download of prices |

## Output Files

**Picks CSV** (auto-saved):
- `sp500_cache/picks_YYYY-MM-DD.csv` — Current stock selections with momentum scores and weights (includes metadata comments)

**Equity Curve** (backtest only):
- `sp500_cache/backtest_equity_curve.csv` — Daily equity curve values for strategy and benchmark

**Price Cache:**
- `sp500_cache/monthly_YYYYMM_YYYYMM.csv` — Monthly price data (auto-managed)
- `sp500_cache/sp500_all_YYYYMMDD.csv` — S&P 500 constituent list

## Output Report Sections

### 1. Current Picks
- Table of selected stocks with momentum %, volatility, and weights
- Sector allocation bar chart
- Signal parameters and universe size

### 2. Portfolio Comparison
- Comparison with previous run
- Kept/new/dropped stock counts and turnover %
- New entries with momentum details
- Weight changes for maintained positions

### 3. Backtest Results
- Summary statistics: Total return, annualized return, volatility, Sharpe, max drawdown, win rate
- Growth of $10,000 initial investment
- Annual returns table with year-end portfolio values
- Strategy vs SPY benchmark comparison

### 4. Tax Impact Analysis (--apply-tax flag)
- Pre-tax and after-tax final values
- Annualized returns (pre and post-tax)
- Total taxes paid and yearly breakdown
- Loss carry-forward tracking
- Tax drag in basis points

## Strategy Parameters

**Momentum Calculation:**
- Lookback: 6 months (default, adjustable with `--lookback`)
- Skip: 1 month (avoids recent mean-reversion, adjustable with `--skip`)
- Weighting: Inverse volatility (position size inversely proportional to annualized volatility)

**Tax Rates:**
- Short-term (holding < 12 months): 35%
- Long-term (holding >= 12 months): 20%
- Monthly rebalancing = short-term rates

## Example Output

```
================================================================================
                                CURRENT PICKS
================================================================================
Signal: 6-month momentum (lookback=6, skip=1)
Weighting: Inverse volatility
Universe: 503 stocks
Date: 2026-03-03

               Company                 Sector Momentum (%) Monthly Vol (%) Ann. Vol (%) Weight (%)
               Sandisk Information Technology      1242.61           57.67      199.79       3.19
     ...

Sector Allocation:
  Information Technology          79.51% #######################################
  Materials                       13.95% ######
  Communication Services           6.54% ###

================================================================================
                            PORTFOLIO COMPARISON
================================================================================
Stocks kept: 10
New entries: 5
Dropped: 0
Turnover: 50.0%

New Entries:
  NEM      82.05% momentum, 11.08% weight
  ...

================================================================================
                             BACKTEST RESULTS
================================================================================
Summary Statistics:
          Metric Strategy Benchmark
          Months       22        22
Total Return (%)   155.73     39.60
 Ann. Return (%)    66.89     19.96
    Ann. Vol (%)    26.94     10.06
    Sharpe Ratio     2.48      1.98
Max Drawdown (%)   -14.08     -7.58
    Win Rate (%)    72.73     68.18

Growth of $10,000:
  Strategy:  $25,573
  Benchmark: $13,960

================================================================================
                           TAX IMPACT ANALYSIS
================================================================================
Strategy: $10,000 -> $25,573 pre-tax -> $19,032 after-tax

Total Taxes Paid: $6,207
```

## Troubleshooting

**No price data retrieved:**
- This may be a network issue. Wait a moment and try again.
- Use `--refresh` to force a fresh download.

**Wikipedia unreachable:**
- The script automatically falls back to cached S&P 500 list.
- On first run without internet, use `--min-cap` with a cached list.

**ModuleNotFoundError:**
- Ensure dependencies are installed in the venv:
  ```powershell
  .\venv\Scripts\pip.exe install numpy pandas requests yfinance lxml
  ```

## License

MIT License

## Author

Created as a comprehensive momentum strategy backtesting tool.
