#!/bin/bash

echo "🚀 Installing Journalist Scraper Dependencies..."
echo ""

pip3 install --upgrade pip

echo "📦 Installing packages..."
pip3 install cloudscraper beautifulsoup4 selenium undetected-chromedriver

echo ""
echo "✅ Installation complete!"
echo ""
echo "Run the scraper with:"
echo "  python3 getjournalistdetails.py"
