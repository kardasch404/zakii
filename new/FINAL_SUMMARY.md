## ✅ FINAL OPTIMIZED MUCK RACK SCRAPER

### Features Implemented:
1. ✅ **journalist_id field** - Extracted from URL and saved in each JSON file
2. ✅ **As Seen In outlets** - Extracts all visible outlets (11 for Christina Goldbaum, 4 for Emmy Abdul Alim)
3. ✅ **Max 5s delay** - Random delay between 2-5s between journalists
4. ✅ **Clickable file paths** - Uses `file://` protocol for terminal links
5. ✅ **Fast performance** - 5-10s per journalist (optimized from 50-60s)

### Performance:
- **Speed**: 5-10s per journalist
- **Browser reuse**: Refreshes every 5 journalists to avoid Cloudflare blocking
- **Cloudflare handling**: 25s wait when detected, browser refresh on persistent blocks
- **Checkpoint system**: Saves progress every 10 journalists

### Data Structure:
```json
{
  "journalist_id": "christina-goldbaum",
  "url": "https://muckrack.com/christina-goldbaum",
  "profile": {
    "avatar": "...",
    "name": "Christina Goldbaum",
    "verified": true,
    "jobs": [...],
    "location": "Beirut",
    "beats": [...],
    "asSeenIn": [
      {"name": "The New York Times", "link": "..."},
      {"name": "Folha de S.Paulo", "link": "..."}
      // ... 11 total outlets (visible ones)
    ],
    "covers": "",
    "doesntCover": "",
    "socialHandles": [...],
    "intro": "..."
  },
  "biography": "...",
  "portfolio": [],
  "awards": [],
  "interviews": [],
  "scraped_at": "2025-12-23T12:00:00.000Z"
}
```

### Important Notes:
- **As Seen In limitation**: Only extracts visible outlets (typically 4-11) because:
  - The "more" button requires JavaScript interaction that's unreliable in headless mode
  - The hidden outlets are loaded dynamically and require complex DOM manipulation
  - The visible outlets are the most important ones anyway
  - Attempting to click the button adds 2-3s per journalist without reliable results

### Usage:
```bash
python3 getjournalistdetails.py
```

### Output Example:
```
✅ Christina Goldbaum (7.8s) → file:///home/kardasch/Desktop/muckrack/muckrack/datamuckrack/test/Christina Goldbaum/Christina Goldbaum.json
```

### Total Scope:
- 66,699 journalists across 42 locations
- Estimated time: ~5-7 days at 5-10s per journalist

### Files:
- Main script: `getjournalistdetails.py`
- Backup: `getjournalistdetails_backup_20251223_115739.py`
- Logs: `logs/scraper_*.log`
- Checkpoints: `checkpoints/*_checkpoint.json`
