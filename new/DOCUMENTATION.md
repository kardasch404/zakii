# Journalist Details Scraper Documentation

## File: `getjournalistdetails.py`

### Purpose
Scrapes detailed journalist profile information from Muck Rack using Selenium WebDriver.

### Key Features
- **Checkpoint System**: Resumes from last position on interruption
- **Progress Tracking**: Real-time ETA and statistics
- **Error Handling**: Saves failed attempts for retry
- **Rate Limiting**: Random delays to avoid detection
- **User Agent Rotation**: Multiple browser signatures

### Data Extracted
- Avatar image
- Name and verification status
- Job titles and outlets
- Location
- Beats (topics covered)
- Media outlets ("As Seen In")
- Coverage preferences (Covers/Doesn't Cover)
- Social media handles
- Profile introduction

### Directory Structure
```
muckrack/
├── datamuckrack/          # Successful scrapes
│   └── {location}/
│       └── {journalist}/
│           └── {journalist}.json
├── failed/                # Failed scrapes
│   └── {location}/
│       └── {journalist}.json
├── checkpoints/           # Resume points
│   └── {location}_checkpoint.json
└── logs/                  # Execution logs
    └── scraper_{timestamp}.log
```

### Input
Reads from: `journalistv2/locations/*.json`

Format:
```json
{
  "location": "New York",
  "journalists": [
    {
      "name": "John Doe",
      "url": "https://muckrack.com/john-doe"
    }
  ]
}
```

### Output
Saves to: `muckrack/datamuckrack/{location}/{name}/{name}.json`

Format:
```json
{
  "url": "https://muckrack.com/john-doe",
  "name": "John Doe",
  "profile": {
    "avatar": "...",
    "verified": true,
    "jobs": [...],
    "location": "...",
    "beats": [...],
    "asSeenIn": [...],
    "covers": "...",
    "doesntCover": "...",
    "socialHandles": [...],
    "intro": "..."
  },
  "scraped_at": "2024-01-01T12:00:00"
}
```

### Usage
```bash
python3 new/getjournalistdetails.py
```

### Key Functions
- `get_random_user_agent()`: Rotates browser user agents
- `sanitize_filename()`: Cleans names for filesystem
- `ProgressTracker`: Tracks progress and estimates completion
- `JournalistScraper.extract_profile()`: Parses HTML for profile data
- `load_checkpoint()` / `save_checkpoint()`: Resume functionality
- `get_already_scraped()`: Skips completed journalists

### Configuration
- Headless Chrome browser
- 2-second delay between requests
- 3 retry attempts per journalist
- Checkpoint saved every 10 journalists
- Progress displayed every 5 journalists
