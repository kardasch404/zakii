# Journalist Scraper - Installation

## Install Required Package (IMPORTANT!)

For best Cloudflare bypass, install undetected-chromedriver:

```bash
pip3 install undetected-chromedriver
```

If you already have the other dependencies, you're good to go!

## Full Dependencies

```bash
pip3 install cloudscraper beautifulsoup4 selenium undetected-chromedriver
```

## Run

```bash
python3 getjournalistdetails.py
```

## Features

- ✅ **Cloudflare Bypass**: Uses undetected-chromedriver for best results
- ✅ **Smart Retries**: 3 attempts with progressive wait times (25s, 35s, 45s)
- ✅ **Checkpoint System**: Resume from where you stopped
- ✅ **Real-time Progress**: See overall stats, ETA, success rate
- ✅ **Failed Tracking**: Separate files for failed journalists
- ✅ **Random Delays**: 1-5s between journalists, 0.5-3s between requests
- ✅ **Human Behavior**: Random scrolling, mouse movements

## Progress Display

```
================================================================================
📊 OVERALL: 119/66868 | ❌ 1 | ⏱️ 0:45:23 | 📈 99.2%
📂 Afghanistan: [45/120] | ETA: 0:15:30
👤 Processing: Kaamil Ahmed
================================================================================
```

## Stop & Resume

Press `Ctrl+C` to stop. Run again to resume from checkpoint!
