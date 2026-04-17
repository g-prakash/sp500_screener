import pandas as pd
import json
from datetime import datetime
import pytz

# Function to load picks from CSV
def load_picks(file_path):
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return pd.DataFrame()  # Return empty DataFrame on error

# Function to load backtest data with fallback
def load_backtest_data(file_path):
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: {file_path} not found, using fallback.")
        return pd.DataFrame()  # Return empty DataFrame on error

# Load monthly picks
picks_file = 'hourly_index_monthly_picks.csv'
monthly_picks = load_picks(picks_file)

# Load backtest data
backtest_file = 'backtest_data.csv'
backtest_data = load_backtest_data(backtest_file)

# Function to convert timezone
def convert_timezone(df, timezone):
    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df['date'].dt.tz_localize('UTC').dt.tz_convert(timezone)
    return df

# Assume 'hourly_returns.csv' is another required file
hourly_returns_file = 'hourly_returns.csv'
try:
    hourly_returns = pd.read_csv(hourly_returns_file)
except FileNotFoundError:
    print(f"Error: {hourly_returns_file} not found.")
    hourly_returns = pd.DataFrame()  # Placeholder empty DataFrame

# Convert timezone if needed
hourly_returns = convert_timezone(hourly_returns, 'America/New_York')

# Generate dashboard
def generate_dashboard():
    chart_data = {
        'hourly_returns': json.dumps(hourly_returns.to_dict(orient='records')),  # Chart data
        'backtest_data': json.dumps(backtest_data.to_dict(orient='records')),  # Chart data
        'monthly_picks': json.dumps(monthly_picks.to_dict(orient='records'))  # Chart data
    }

    # Here, include your logic to create an HTML dashboard
    # This is a placeholder
    html_content = f"""
    <html>
    <head>
        <link rel='stylesheet' type='text/css' href='styles.css'>
    </head>
    <body>
        <div id='dashboard'>
            <h1>Dashboard</h1>
            <div id='hourly-returns'>
                <h2>Hourly Returns</h2>
                <script>const chartData = {chart_data['hourly_returns']};</script>
            </div>
            <div id='backtest-results'>
                <h2>Backtest Results</h2>
                <script>const backtestData = {chart_data['backtest_data']};</script>
            </div>
            <div id='monthly-picks'>
                <h2>Monthly Picks</h2>
                <script>const picksData = {chart_data['monthly_picks']};</script>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

# Call the function to generate the dashboard
if __name__ == '__main__':
    dashboard_html = generate_dashboard()
    # Output the dashboard to a file (not shown here)
