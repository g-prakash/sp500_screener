# 📊 S&P 500 Momentum Portfolio - Live Dashboard

A momentum-based stock picking strategy with real-time performance tracking, backtesting, and GitHub Pages deployment.

## 🚀 Features

- **Hourly Returns Tracking**: Real-time portfolio performance monitoring
- **Monthly Stock Picks**: Automated momentum-based stock selection on the 1st of each month
- **Backtest Analysis**: Historical strategy performance vs S&P 500 benchmark (2016-present)
- **Live Dashboard**: Interactive web dashboard accessible via GitHub Pages
- **Automated Workflows**: GitHub Actions for monthly picks and hourly updates

## 📈 Dashboard Views

1. **Hourly Returns** - Portfolio vs SPY benchmark with interactive chart
2. **Backtest Results** - Historical momentum strategy performance
3. **Monthly Picks** - Current and historical stock picks with weights

## 🔧 Setup & Deployment

### Prerequisites

- GitHub account
- Python 3.11+
- pip with: `pandas`, `numpy`, `yfinance`, `requests`, `lxml`, `matplotlib`, `python-dateutil`

### Deploy to GitHub Pages

1. **Initialize Git repository** (if not already done):
```bash
git init
git add .
git commit -m "Initial commit: Portfolio dashboard"
```

2. **Create GitHub repository**:
   - Go to https://github.com/new
   - Create a new public repository (e.g., `sp500-momentum`)

3. **Push to GitHub**:
```bash
git remote add origin https://github.com/YOUR_USERNAME/sp500-momentum.git
git branch -M main
git push -u origin main
```

4. **Enable GitHub Pages**:
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main` / `/(root)` folder
   - Click Save

5. **Enable GitHub Actions**:
   - Go to repository Settings → Actions → General
   - Workflows permissions: Select "Read and write permissions"
   - Save

### Access Your Dashboard

Your live dashboard will be available at:
```
https://YOUR_USERNAME.github.io/sp500-momentum/portfolio_dashboard.html
```

Or create an index.html redirector:

```bash
echo '<script>window.location.href="./portfolio_dashboard.html"</script>' > index.html
git add index.html
git commit -m "Add index.html redirector"
git push
```

Then access at: `https://YOUR_USERNAME.github.io/sp500-momentum/`

## ⏰ Automated Workflows

### Monthly Picks (1st of each month at 9:30 AM ET)

- **File**: `.github/workflows/monthly-picks.yml`
- **Trigger**: 1st day of month @ 13:30 UTC (9:30 AM ET)
- **Action**: Runs `sp500_momentum.py`, generates new picks, commits to repo

### Hourly Returns (Every hour Mon-Fri 9:05 AM - 4:05 PM ET)

- **File**: `.github/workflows/hourly-returns.yml`
- **Trigger**: Mon-Fri every hour during market hours
- **Action**: Runs `hourly_retrurn.py`, updates dashboard, commits to repo

### Deploy to Pages (On push)

- **File**: `.github/workflows/deploy.yml`
- **Trigger**: Push to main branch
- **Action**: Deploys latest dashboard to GitHub Pages

## 🔄 Manual Triggers

You can manually trigger workflows anytime:

1. Go to repository → Actions tab
2. Select workflow (e.g., "Generate Monthly Picks")
3. Click "Run workflow" → "Run workflow"

## 📊 File Structure

```
.
├── hourly_retrurn.py              # Update hourly returns
├── sp500_momentum.py              # Generate monthly picks
├── generate_dashboard.py           # Create interactive dashboard
├── portfolio_dashboard.html        # Live dashboard (GitHub Pages)
├── hourly_index_picks_*.csv       # Hourly performance data
├── sp500_cache/
│   ├── picks_*.csv               # Monthly picks archive
│   ├── backtest_equity_curve.csv # Historical backtest
│   └── ...
├── .github/workflows/
│   ├── monthly-picks.yml         # Monthly picks automation
│   ├── hourly-returns.yml        # Hourly returns automation
│   └── deploy.yml                # GitHub Pages deployment
└── README.md                      # This file
```

## 🔐 Security Notes

- All scripts run with read-only access to public data (yfinance)
- GitHub Actions uses default tokens (no credentials needed)
- Repository should be **public** for GitHub Pages free tier
- No sensitive data is stored or deployed

## 📝 Customization

### Change Monthly Pick Timing
Edit `.github/workflows/monthly-picks.yml`, line with `cron:` field:
```yaml
# Format: minute hour day month day-of-week
- cron: '30 13 1 * *'  # 9:30 AM ET on 1st of month
```

### Change Hourly Update Timing
Edit `.github/workflows/hourly-returns.yml`, line with `cron:` field:
```yaml
- cron: '5 13-20 * * 1-5'  # Every hour 9:05 AM - 4:05 PM ET, Mon-Fri
```

### Modify Dashboard
Edit `generate_dashboard.py` and `hourly_retrurn.py` to customize metrics and charts.

## 🐛 Troubleshooting

### Workflows not running?
- Check Actions are enabled in Settings
- Verify workflows have read/write permissions
- Check branch is set to `main`

### Dashboard not updating?
- Manually trigger workflow from Actions tab
- Check workflow logs for errors
- Verify files are being committed and pushed

### Data not loading?
- Ensure CSV and HTML files are in repository root
- Check file names match in `generate_dashboard.py`
- Verify GitHub Pages is enabled in Settings

## 📞 Support

For issues with:
- **yfinance**: https://github.com/ranaroussi/yfinance
- **GitHub Actions**: https://github.com/actions
- **GitHub Pages**: https://docs.github.com/en/pages

## 📄 License

MIT License - feel free to modify and redistribute
