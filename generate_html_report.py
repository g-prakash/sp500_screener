import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Load the CSV data
csv_file = Path('hourly_index_picks_2026-03-03.csv')
df = pd.read_csv(csv_file, parse_dates=[0])
df.columns = ['DateTime', 'Portfolio Value', 'SPY Value']

# Format data for JavaScript
dates_json = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M').tolist()
portfolio_json = df['Portfolio Value'].tolist()
spy_json = df['SPY Value'].tolist()

# Calculate statistics
portfolio_start = df['Portfolio Value'].iloc[0]
portfolio_end = df['Portfolio Value'].iloc[-1]
portfolio_return = (portfolio_end - portfolio_start) / portfolio_start * 100

spy_start = df['SPY Value'].iloc[0]
spy_end = df['SPY Value'].iloc[-1]
spy_return = (spy_end - spy_start) / spy_start * 100

portfolio_max = df['Portfolio Value'].max()
portfolio_min = df['Portfolio Value'].min()
portfolio_max_drawdown = (portfolio_min - portfolio_start) / portfolio_start * 100

spy_max = df['SPY Value'].max()
spy_min = df['SPY Value'].min()
spy_max_drawdown = (spy_min - spy_start) / spy_start * 100

fig.add_trace(go.Scatter(
    x=df['DateTime'],
    y=df['Portfolio Value'],
    mode='lines',
    name=f'Portfolio ({portfolio_return:+.2f}%)',
    line=dict(color='#1f77b4', width=2),
    hovertemplate='<b>Portfolio</b><br>%{x}<br>Value: $%{y:,.2f}<extra></extra>'
))

fig.add_trace(go.Scatter(
    x=df['DateTime'],
    y=df['SPY Value'],
    mode='lines',
    name=f'SPY ({spy_return:+.2f}%)',
    line=dict(color='#ff7f0e', width=2),
    hovertemplate='<b>SPY</b><br>%{x}<br>Value: $%{y:,.2f}<extra></extra>'
))

# Add starting value reference line
fig.add_hline(y=10000, line_dash="dash", line_color="gray", 
              annotation_text="Start ($10,000)", annotation_position="right")

fig.update_layout(
    title='Historical Returns: Momentum Portfolio vs SPY',
    title_font_size=20,
    xaxis_title='Date / Time (ET)',
    yaxis_title='Portfolio Value ($)',
    template='plotly_white',
    hovermode='x unified',
    height=600,
    font=dict(size=11),
    margin=dict(l=60, r=60, t=80, b=60)
)

html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Momentum Portfolio - Historical Returns</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
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
            font-weight: 700;
        }}
        
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px 20px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        
        .stat-card.spy {{
            border-left-color: #ff7f0e;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #1f77b4;
        }}
        
        .stat-card.spy .stat-value {{
            color: #ff7f0e;
        }}
        
        .stat-subvalue {{
            font-size: 12px;
            color: #999;
            margin-top: 8px;
        }}
        
        .chart-container {{
            padding: 20px;
        }}
        
        #chart {{
            width: 100%;
            height: 600px;
        }}
        
        .data-section {{
            padding: 30px 20px;
            background-color: #f8f9fa;
        }}
        
        .data-section h2 {{
            font-size: 18px;
            margin-bottom: 20px;
            color: #333;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        
        th {{
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        tr:hover {{
            background-color: #f0f2f5;
        }}
        
        .footer {{
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e9ecef;
        }}
        
        .positive {{ color: #28a745; font-weight: 600; }}
        .negative {{ color: #dc3545; font-weight: 600; }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 24px; }}
            .stats-grid {{ grid-template-columns: 1fr; }}
            .stat-value {{ font-size: 22px; }}
            
            table {{
                font-size: 12px;
            }}
            
            th, td {{ padding: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Momentum Portfolio Performance</h1>
            <p>Historical Returns Analysis — {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Portfolio Return</div>
                <div class="stat-value positive">{portfolio_return:+.2f}%</div>
                <div class="stat-subvalue">Start: ${portfolio_start:,.2f} → End: ${portfolio_end:,.2f}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Max Drawdown</div>
                <div class="stat-value negative">{portfolio_max_drawdown:.2f}%</div>
                <div class="stat-subvalue">Low: ${portfolio_min:,.2f}</div>
            </div>
            
            <div class="stat-card spy">
                <div class="stat-label">SPY Return</div>
                <div class="stat-value">{spy_return:+.2f}%</div>
                <div class="stat-subvalue">Start: ${spy_start:,.2f} → End: ${spy_end:,.2f}</div>
            </div>
            
            <div class="stat-card spy">
                <div class="stat-label">Outperformance</div>
                <div class="stat-value positive">{portfolio_return - spy_return:+.2f}%</div>
                <div class="stat-subvalue">vs SPY Benchmark</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div id="chart"></div>
        </div>
        
        <div class="data-section">
            <h2>Data Summary</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Portfolio</th>
                        <th>SPY</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Starting Value</td>
                        <td><strong>${portfolio_start:,.2f}</strong></td>
                        <td><strong>${spy_start:,.2f}</strong></td>
                    </tr>
                    <tr>
                        <td>Ending Value</td>
                        <td><strong>${portfolio_end:,.2f}</strong></td>
                        <td><strong>${spy_end:,.2f}</strong></td>
                    </tr>
                    <tr>
                        <td>Total Return</td>
                        <td><span class="positive">{portfolio_return:+.2f}%</span></td>
                        <td><span class="{('positive' if spy_return >= 0 else 'negative')}">{spy_return:+.2f}%</span></td>
                    </tr>
                    <tr>
                        <td>Peak Value</td>
                        <td>${portfolio_max:,.2f}</td>
                        <td>${spy_max:,.2f}</td>
                    </tr>
                    <tr>
                        <td>Low Value</td>
                        <td>${portfolio_min:,.2f}</td>
                        <td>${spy_min:,.2f}</td>
                    </tr>
                    <tr>
                        <td>Max Drawdown</td>
                        <td><span class="negative">{portfolio_max_drawdown:.2f}%</span></td>
                        <td><span class="negative">{spy_max_drawdown:.2f}%</span></td>
                    </tr>
                    <tr>
                        <td>Outperformance</td>
                        <td colspan="2"><span class="positive">{portfolio_return - spy_return:+.2f}%</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Data from {csv_file} | Last updated: {df['DateTime'].iloc[-1]} | Portfolio vs S&P 500 (SPY) Benchmark</p>
        </div>
    </div>
    
    <script>
        var data = {json.dumps([
            dict(
                x=df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                y=df['Portfolio Value'].tolist(),
                mode='lines',
                name='Portfolio ({portfolio_return:+.2f}%)',
                line=dict(color='#1f77b4', width=2),
            ),
            dict(
                x=df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                y=df['SPY Value'].tolist(),
                mode='lines',
                name='SPY ({spy_return:+.2f}%)',
                line=dict(color='#ff7f0e', width=2),
            )
        ])};
        
        var layout = {{
            title: 'Historical Returns: Momentum Portfolio vs SPY',
            xaxis: {{ title: 'Date / Time (ET)' }},
            yaxis: {{ title: 'Portfolio Value ($)' }},
            template: 'plotly_white',
            hovermode: 'x unified',
            height: 600,
            margin: {{ l: 60, r: 60, t: 50, b: 60 }}
        }};
        
        Plotly.newPlot('chart', data, layout, {{responsive: true}});
    </script>
</body>
</html>
"""

# Save HTML file
output_file = Path('historical_returns.html')
with open(output_file, 'w') as f:
    f.write(html_content)

print(f"✓ HTML report generated: {output_file}")
print(f"  Portfolio Return: {portfolio_return:+.2f}%")
print(f"  SPY Return: {spy_return:+.2f}%")
print(f"  Outperformance: {portfolio_return - spy_return:+.2f}%")
