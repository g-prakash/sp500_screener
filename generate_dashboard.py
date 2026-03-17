import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Load hourly returns data
hourly_file = Path('hourly_index_picks_2026-03-03.csv')
hourly_df = pd.read_csv(hourly_file, parse_dates=[0])
hourly_df.columns = ['DateTime', 'Portfolio Value', 'SPY Value']

# Load backtest equity curve data
backtest_file = Path('sp500_cache/backtest_equity_curve.csv')
backtest_df = pd.read_csv(backtest_file, parse_dates=['Date'])
backtest_df.columns = ['Date', 'Strategy', 'Benchmark']

# Load picks files - FILTER for first day of month only
cache_dir = Path('sp500_cache')
pick_files = sorted(cache_dir.glob('picks_*.csv'))

picks_data = {}
for pick_file in pick_files[-12:]:  # Get last 12 months
    date_str = pick_file.stem.split('_')[1]  # Extract date from filename
    # Only include picks from the first day of the month (YYYY-MM-01)
    if date_str.endswith('-01'):
        df = pd.read_csv(pick_file, comment='#')
        picks_data[date_str] = df

# Format data for charts
hourly_dates = hourly_df['DateTime'].dt.strftime('%Y-%m-%d %H:%M').tolist()
hourly_portfolio = hourly_df['Portfolio Value'].tolist()
hourly_spy = hourly_df['SPY Value'].tolist()

# Calculate returns
portfolio_start = hourly_df['Portfolio Value'].iloc[0]
portfolio_end = hourly_df['Portfolio Value'].iloc[-1]
portfolio_return = (portfolio_end - portfolio_start) / portfolio_start * 100

spy_start = hourly_df['SPY Value'].iloc[0]
spy_end = hourly_df['SPY Value'].iloc[-1]
spy_return = (spy_end - spy_start) / spy_start * 100

# Calculate backtest returns with normalization to $10,000
backtest_dates = backtest_df['Date'].dt.strftime('%Y-%m-%d').tolist()

# Normalize both strategy and benchmark to start at $10,000
backtest_strat_start = backtest_df['Strategy'].iloc[0]
backtest_bench_start = backtest_df['Benchmark'].iloc[0]
backtest_strat_end = backtest_df['Strategy'].iloc[-1]
backtest_bench_end = backtest_df['Benchmark'].iloc[-1]

# Calculate returns BEFORE normalization
backtest_strat_return = (backtest_strat_end - backtest_strat_start) / backtest_strat_start * 100
backtest_bench_return = (backtest_bench_end - backtest_bench_start) / backtest_bench_start * 100

# Normalize series to $10,000 start
backtest_strategy = (backtest_df['Strategy'] / backtest_strat_start * 10000).tolist()
backtest_benchmark = (backtest_df['Benchmark'] / backtest_bench_start * 10000).tolist()

# Use normalized start value
backtest_strat_start_normalized = 10000.0
backtest_bench_start_normalized = 10000.0
backtest_strat_end_normalized = backtest_strategy[-1]
backtest_bench_end_normalized = backtest_benchmark[-1]

# Build picks HTML tables
picks_html = ""
for date_str in sorted(picks_data.keys(), reverse=True):
    df = picks_data[date_str]
    picks_html += f"""
    <div class="picks-month">
        <h3>{date_str}</h3>
        <table class="picks-table">
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Weight (%)</th>
                </tr>
            </thead>
            <tbody>
    """
    for _, row in df.iterrows():
        ticker = row['Ticker']
        weight = float(row['Weight (%)'])
        picks_html += f"                <tr><td>{ticker}</td><td>{weight:.2f}%</td></tr>\n"
    picks_html += """
            </tbody>
        </table>
    </div>
    """

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .controls {{
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .controls label {{
            font-weight: 600;
            color: #667eea;
        }}
        
        .controls select {{
            padding: 10px 15px;
            border: 2px solid #667eea;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            background: white;
        }}
        
        .view-container {{
            padding: 30px 20px;
            display: none;
        }}
        
        .view-container.active {{
            display: block;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }}
        
        .stat-label {{
            font-size: 12px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            margin-top: 8px;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 30px;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        
        canvas {{
            max-height: 400px;
        }}
        
        .picks-section {{
            padding: 30px 20px;
        }}
        
        .picks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .picks-month {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .picks-month h3 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 16px;
        }}
        
        .picks-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        
        .picks-table th {{
            background: #667eea;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: 600;
        }}
        
        .picks-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .picks-table tr:hover {{
            background: #e8edf7;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e9ecef;
        }}
        
        .positive {{ color: #28a745; font-weight: 600; }}
        .negative {{ color: #dc3545; font-weight: 600; }}
        
        @media (max-width: 768px) {{
            .controls {{
                flex-direction: column;
                align-items: flex-start;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .picks-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Portfolio Performance Dashboard</h1>
            <p>Real-time Analysis & Historical Stock Picks</p>
        </div>
        
        <div class="controls">
            <label for="viewSelector">View:</label>
            <select id="viewSelector" onchange="switchView(this.value)">
                <option value="hourly">Hourly Returns</option>
                <option value="backtest">Backtest Results</option>
                <option value="monthly">Monthly Picks</option>
            </select>
        </div>
        
        <!-- HOURLY RETURNS VIEW -->
        <div id="hourly-view" class="view-container active">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Portfolio Return</div>
                    <div class="stat-value positive">{portfolio_return:+.2f}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">SPY Return</div>
                    <div class="stat-value">{spy_return:+.2f}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Outperformance</div>
                    <div class="stat-value positive">{portfolio_return - spy_return:+.2f}%</div>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="hourlyChart"></canvas>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="color: #667eea; margin-bottom: 15px;">Performance Summary</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;"><strong>Portfolio Start Value</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;">${portfolio_start:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;"><strong>Portfolio End Value</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;">${portfolio_end:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;"><strong>SPY Start Value</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;">${spy_start:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px;"><strong>SPY End Value</strong></td>
                        <td style="padding: 10px;">${spy_end:,.2f}</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <!-- BACKTEST RESULTS VIEW -->
        <div id="backtest-view" class="view-container">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Strategy Return (Monthly)</div>
                    <div class="stat-value positive">{backtest_strat_return:+.2f}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Benchmark Return (Monthly)</div>
                    <div class="stat-value">{backtest_bench_return:+.2f}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Outperformance</div>
                    <div class="stat-value positive">{backtest_strat_return - backtest_bench_return:+.2f}%</div>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="backtestChart"></canvas>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="color: #667eea; margin-bottom: 15px;">Backtest Performance Summary</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;"><strong>Strategy Start Value</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;">${backtest_strat_start_normalized:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;"><strong>Strategy End Value</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;">${backtest_strat_end_normalized:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;"><strong>Benchmark Start Value</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef;">${backtest_bench_start_normalized:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px;"><strong>Benchmark End Value</strong></td>
                        <td style="padding: 10px;">${backtest_bench_end_normalized:,.2f}</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <!-- MONTHLY PICKS VIEW -->
        <div id="monthly-view" class="view-container">
            <div class="picks-section">
                <h2 style="color: #667eea; margin-bottom: 20px;"> Monthly Stock Picks</h2>
                <div class="picks-grid">
                    {picks_html}
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Portfolio Dashboard | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data from MultiDay Analysis</p>
        </div>
    </div>
    
    <script>
        function switchView(view) {{
            document.querySelectorAll('.view-container').forEach(el => {{
                el.classList.remove('active');
            }});
            document.getElementById(view + '-view').classList.add('active');
        }}
        
        // Hourly Chart
        const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
        const hourlyDates = {json.dumps(hourly_dates)};
        const hourlyPortfolio = {json.dumps(hourly_portfolio)};
        const hourlySpy = {json.dumps(hourly_spy)};
        
        new Chart(hourlyCtx, {{
            type: 'line',
            data: {{
                labels: hourlyDates,
                datasets: [
                    {{
                        label: 'Portfolio ({portfolio_return:+.2f}%)',
                        data: hourlyPortfolio,
                        borderColor: '#1f77b4',
                        backgroundColor: 'rgba(31, 119, 180, 0.05)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 6
                    }},
                    {{
                        label: 'SPY ({spy_return:+.2f}%)',
                        data: hourlySpy,
                        borderColor: '#ff7f0e',
                        backgroundColor: 'rgba(255, 127, 14, 0.05)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 6
                    }},
                    {{
                        label: 'Initial Investment ($10,000)',
                        type: 'line',
                        data: Array(hourlyDates.length).fill(10000),
                        borderColor: '#999999',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        tension: 0
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        ticks: {{
                            callback: function(value) {{
                                return '$' + value.toLocaleString();
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Backtest Chart
        const backtestCtx = document.getElementById('backtestChart').getContext('2d');
        const backtestDates = {json.dumps(backtest_dates)};
        const backtestStrategy = {json.dumps(backtest_strategy)};
        const backtestBenchmark = {json.dumps(backtest_benchmark)};
        
        new Chart(backtestCtx, {{
            type: 'line',
            data: {{
                labels: backtestDates,
                datasets: [
                    {{
                        label: 'Strategy ({backtest_strat_return:+.2f}%)',
                        data: backtestStrategy,
                        borderColor: '#1f77b4',
                        backgroundColor: 'rgba(31, 119, 180, 0.05)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 6
                    }},
                    {{
                        label: 'Benchmark ({backtest_bench_return:+.2f}%)',
                        data: backtestBenchmark,
                        borderColor: '#ff7f0e',
                        backgroundColor: 'rgba(255, 127, 14, 0.05)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 6
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        ticks: {{
                            callback: function(value) {{
                                return '$' + value.toLocaleString();
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

# Save to file
output_file = Path('portfolio_dashboard.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✓ Dashboard generated: {output_file}")
print(f"  Available picks dates: {', '.join(sorted(picks_data.keys(), reverse=True))}")
print(f"  Portfolio Return: {portfolio_return:+.2f}%")
print(f"  SPY Return: {spy_return:+.2f}%")
