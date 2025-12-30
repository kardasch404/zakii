#!/bin/bash
# Run the optimized Muck Rack scraper

cd /home/kardasch/Desktop/muckrack/new

echo "🚀 Starting Muck Rack Scraper..."
echo "📊 This will update all 66,686 journalists"
echo "⏱️  Estimated time: 5-7 days at 6-10s per journalist"
echo ""
echo "Press Ctrl+C to stop at any time (progress is saved)"
echo ""

python3 getjournalistdetails.py
