#!/bin/bash
# Deploy to GitHub Pages setup script

echo "🚀 S&P 500 Momentum Portfolio - GitHub Deployment Setup"
echo "========================================================"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install git first."
    exit 1
fi

echo "Step 1: Initialize Git Repository"
echo "=================================="

if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit: Portfolio dashboard with automated workflows"
    echo "✓ Repository initialized"
else
    echo "✓ Git repository already exists"
fi

echo ""
echo "Step 2: GitHub Repository Setup"
echo "=============================="
echo "Please follow these steps:"
echo "1. Go to https://github.com/new"
echo "2. Create a new repository (e.g., 'sp500-momentum')"
echo "3. Choose 'Public' for GitHub Pages (free tier)"
echo ""
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your repository name (default: sp500-momentum): " REPO_NAME
REPO_NAME="${REPO_NAME:-sp500-momentum}"

echo ""
echo "Step 3: Connecting to GitHub"
echo "============================"

REMOTE_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
echo "Adding remote: $REMOTE_URL"

git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
git branch -M main

echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✓ Successfully pushed to GitHub!"
else
    echo "❌ Failed to push. Please check your credentials and try again."
    exit 1
fi

echo ""
echo "Step 4: Enable GitHub Pages"
echo "============================"
echo "Please complete these steps in GitHub:"
echo "1. Go to: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/settings/pages"
echo "2. Under 'Source', select:"
echo "   - Branch: main"
echo "   - Folder: / (root)"
echo "3. Click Save"
echo ""

echo "Step 5: Enable GitHub Actions"
echo "============================"
echo "Please complete these steps in GitHub:"
echo "1. Go to: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/settings/actions"
echo "2. Under 'Workflow permissions', select:"
echo "   - 'Read and write permissions'"
echo "3. Click Save"
echo ""

echo "✅ Deployment setup complete!"
echo ""
echo "📊 Your dashboard will be available at:"
echo "   https://${GITHUB_USERNAME}.github.io/${REPO_NAME}/"
echo ""
echo "⏰ Automated Workflows:"
echo "   • Monthly picks: 1st of month @ 9:30 AM ET"
echo "   • Hourly returns: Every hour (market hours)"
echo "   • Dashboard: Deploys on every push"
echo ""
echo "📝 See DEPLOYMENT_GUIDE.md for full details"
