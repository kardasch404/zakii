#!/usr/bin/env python3
"""Production Journalist Scraper - Architect's Version"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set
import time
import random
from urllib.parse import quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Configuration
BASE_DIR = Path(__file__).parent.parent
LOCATIONS_DIR = BASE_DIR / "journalistv2" / "locations"
DATA_DIR = BASE_DIR / "muckrack" / "datamuckrack"
FAILED_DIR = BASE_DIR / "muckrack" / "failed"
LOG_DIR = BASE_DIR / "logs"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"

# Create directories
for d in [DATA_DIR, FAILED_DIR, LOG_DIR, CHECKPOINT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Logging setup
log_file = LOG_DIR / f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file)]
)
logger = logging.getLogger(__name__)

def get_random_user_agent():
    """Rotate user agents"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    ]
    return random.choice(agents)

def sanitize_filename(name):
    """Clean filename for filesystem"""
    return name.replace('/', '-').replace('\\', '-').replace(':', '-').replace('?', '').replace('*', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')

class ProgressTracker:
    """Track progress and estimate time"""
    def __init__(self, total_journalists, total_locations):
        self.total_journalists = total_journalists
        self.total_locations = total_locations
        self.scraped = 0
        self.failed = 0
        self.skipped = 0
        self.current_location = ""
        self.current_location_index = 0
        self.current_location_total = 0
        self.current_location_scraped = 0
        self.start_time = time.time()
        self.location_start_time = time.time()
        self.journalist_times = []
        
    def update(self, scraped=0, failed=0, skipped=0, elapsed=0):
        self.scraped += scraped
        self.failed += failed
        self.skipped += skipped
        self.current_location_scraped += scraped
        if elapsed > 0:
            self.journalist_times.append(elapsed)
        
    def set_location(self, location_name, location_index, location_total):
        self.current_location = location_name
        self.current_location_index = location_index
        self.current_location_total = location_total
        self.current_location_scraped = 0
        self.location_start_time = time.time()
        
    def get_stats(self):
        total_processed = self.scraped + self.failed + self.skipped
        overall_pct = (total_processed / self.total_journalists * 100) if self.total_journalists > 0 else 0
        location_pct = (self.current_location_scraped / self.current_location_total * 100) if self.current_location_total > 0 else 0
        
        avg_time = sum(self.journalist_times) / len(self.journalist_times) if self.journalist_times else 0
        remaining = self.total_journalists - total_processed
        eta_seconds = avg_time * remaining if avg_time > 0 else 0
        
        return {
            'overall_pct': overall_pct,
            'location_pct': location_pct,
            'avg_time': avg_time,
            'eta': str(timedelta(seconds=int(eta_seconds))),
            'elapsed': str(timedelta(seconds=int(time.time() - self.start_time)))
        }
        
    def print_status(self):
        stats = self.get_stats()
        print(f"\n{'='*80}")
        print(f"📊 OVERALL: {self.scraped + self.failed + self.skipped:,}/{self.total_journalists:,} ({stats['overall_pct']:.1f}%)")
        print(f"✅ {self.scraped:,} | ❌ {self.failed:,} | ⏭️ {self.skipped:,}")
        print(f"⏱️  Avg: {stats['avg_time']:.1f}s | ETA: {stats['eta']} | Elapsed: {stats['elapsed']}")
        print(f"📍 Location: {self.current_location} ({self.current_location_index}/{self.total_locations}) - {stats['location_pct']:.1f}%")
        print(f"{'='*80}\n")

class JournalistScraper:
    """Main scraper class"""
    def __init__(self, location_name: str):
        self.location = location_name
        self.driver = None
        
    def init_driver(self):
        """Initialize Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={get_random_user_agent()}')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def try_navigate(self, url: str, max_retries: int = 3) -> bool:
        """Navigate with retries"""
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    self.driver.delete_all_cookies()
                    time.sleep(2)
                
                self.driver.get(url)
                time.sleep(random.uniform(0.5, 1.0))
                
                if 'mr-card-content' in self.driver.page_source:
                    return True
                    
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to load {url}: {e}")
                    return False
                time.sleep(2)
        return False
    
    def prepend_base_url(self, link: str) -> str:
        if not link or link.startswith('http'):
            return link
        return f'https://muckrack.com{link}'
    
    def extract_profile(self) -> dict:
        """Extract profile data"""
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        container = soup.select_one('div.mr-card-content')
        if not container:
            return {}
        
        profile = {}
        
        # Avatar
        if img := container.select_one('img[src*="profile/images"]'):
            profile['avatar'] = img.get('src', '')
        
        # Name
        if name := container.select_one('h1.profile-name'):
            profile['name'] = name.get_text(strip=True)
        
        # Verified
        profile['verified'] = bool(container.select_one('small.profile-verified'))
        
        # Jobs
        jobs = []
        for item in container.select('ul.mr-person-job-items li.mr-person-job-item'):
            outlet = item.select_one('a')
            if outlet:
                text = item.get_text(strip=True)
                title = text.split(',')[0].strip()
                jobs.append({
                    'title': title,
                    'outlet': outlet.get_text(strip=True),
                    'outletLink': self.prepend_base_url(outlet.get('href', ''))
                })
        profile['jobs'] = jobs
        
        # Location
        if loc := container.select_one('div.person-details-location span'):
            profile['location'] = loc.get_text(strip=True)
        
        # Beats
        beats = []
        if beats_div := container.select_one('div.person-details-beats div'):
            for a in beats_div.select('a'):
                beats.append({
                    'name': a.get_text(strip=True),
                    'link': self.prepend_base_url(a.get('href', ''))
                })
        profile['beats'] = beats
        
        # As seen in
        as_seen = []
        for item in container.select('div.profile-details-item a'):
            as_seen.append({
                'name': item.get_text(strip=True),
                'link': self.prepend_base_url(item.get('href', ''))
            })
        if hidden_span := container.select_one('span.js-as-seen-in-hidden'):
            for a in hidden_span.select('a'):
                as_seen.append({
                    'name': a.get_text(strip=True),
                    'link': self.prepend_base_url(a.get('href', ''))
                })
        profile['asSeenIn'] = as_seen
        
        # Covers
        profile['covers'] = ''
        profile['doesntCover'] = ''
        for item in container.select('div.profile-details-item'):
            txt = item.get_text()
            if 'Covers:' in txt:
                profile['covers'] = txt.split('Covers:', 1)[1].strip()
            elif "Doesn't Cover:" in txt:
                profile['doesntCover'] = txt.split("Doesn't Cover:", 1)[1].strip()
        
        # Social & intro
        handles = []
        if social := container.select_one('div.fs-5.fs-md-6.my-5'):
            for a in social.select('a.tweet-url.username'):
                handles.append({
                    'handle': a.get_text(strip=True),
                    'link': self.prepend_base_url(a.get('href', ''))
                })
            profile['intro'] = social.get_text(strip=True)
        profile['socialHandles'] = handles
        
        return profile
    
    def scrape_journalist(self, journalist: Dict) -> Dict:
        """Scrape single journalist"""
        url = journalist['url']
        
        self.init_driver()
        
        if not self.try_navigate(url):
            raise Exception('Navigation failed')
        
        profile = self.extract_profile()
        
        return {
            'url': url,
            'name': profile.get('name', journalist['name']),
            'profile': profile,
            'scraped_at': datetime.now().isoformat()
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def load_checkpoint(location):
    """Load checkpoint"""
    checkpoint_file = CHECKPOINT_DIR / f"{location}_checkpoint.json"
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
            return set(data.get('scraped_urls', []))
    return set()

def save_checkpoint(location, scraped_urls):
    """Save checkpoint"""
    checkpoint_file = CHECKPOINT_DIR / f"{location}_checkpoint.json"
    with open(checkpoint_file, 'w') as f:
        json.dump({
            'location': location,
            'scraped_urls': list(scraped_urls),
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

def save_journalist_data(journalist, data):
    """Save journalist data"""
    location = sanitize_filename(journalist['location'])
    name = sanitize_filename(journalist['name'])
    
    journalist_dir = DATA_DIR / location / name
    journalist_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = journalist_dir / f"{name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return json_path

def save_failed(journalist, error):
    """Save failed journalist"""
    location = sanitize_filename(journalist['location'])
    name = sanitize_filename(journalist['name'])
    
    failed_dir = FAILED_DIR / location
    failed_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = failed_dir / f"{name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'url': journalist['url'],
            'name': journalist['name'],
            'location': journalist['location'],
            'error': str(error),
            'failed_at': datetime.now().isoformat()
        }, f, indent=2)
    
    return json_path

def get_all_journalists():
    """Load all journalists from locations"""
    all_journalists = []
    locations = []
    
    for json_file in sorted(LOCATIONS_DIR.glob("*.json")):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            location = data.get('location', json_file.stem).title()
            journalists = data.get('journalists', [])
            
            locations.append({'name': location, 'count': len(journalists)})
            
            for j in journalists:
                all_journalists.append({
                    'name': j['name'],
                    'url': j['url'],
                    'location': location
                })
    
    return all_journalists, locations

def get_already_scraped():
    """Get already scraped URLs"""
    scraped = set()
    if DATA_DIR.exists():
        for json_file in DATA_DIR.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'url' in data:
                        scraped.add(data['url'])
            except:
                pass
    return scraped

def main():
    print("\n" + "="*80)
    print("🚀 JOURNALIST SCRAPER - PRODUCTION VERSION")
    print("="*80 + "\n")
    
    # Load data
    logger.info("🔍 Scanning already scraped...")
    already_scraped = get_already_scraped()
    logger.info(f"✅ Found {len(already_scraped):,} already scraped")
    
    logger.info("📋 Loading journalists...")
    all_journalists, locations = get_all_journalists()
    logger.info(f"✅ Total: {len(all_journalists):,} across {len(locations)} locations")
    
    # Find missing
    missing = [j for j in all_journalists if j['url'] not in already_scraped]
    logger.info(f"🎯 Missing: {len(missing):,}")
    
    if not missing:
        logger.info("✅ All done!")
        return
    
    # Group by location
    missing_by_location = {}
    for j in missing:
        loc = j['location']
        if loc not in missing_by_location:
            missing_by_location[loc] = []
        missing_by_location[loc].append(j)
    
    # Initialize tracker
    tracker = ProgressTracker(len(missing), len(missing_by_location))
    
    # Process each location
    for loc_idx, (location_name, journalists) in enumerate(sorted(missing_by_location.items(), key=lambda x: len(x[1]), reverse=True), 1):
        tracker.set_location(location_name, loc_idx, len(journalists))
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📍 LOCATION: {location_name} ({loc_idx}/{len(missing_by_location)})")
        logger.info(f"📊 To scrape: {len(journalists)}")
        logger.info(f"{'='*80}\n")
        
        scraper = JournalistScraper(location_name)
        checkpoint_urls = load_checkpoint(location_name)
        
        for idx, journalist in enumerate(journalists, 1):
            if journalist['url'] in checkpoint_urls:
                tracker.update(skipped=1)
                continue
                
            try:
                start = time.time()
                
                # Print with clickable path
                location_clean = sanitize_filename(journalist['location'])
                name_clean = sanitize_filename(journalist['name'])
                path = DATA_DIR / location_clean / name_clean / f"{name_clean}.json"
                clickable = f"file://{quote(str(path.absolute()))}"
                
                print(f"\n[{idx}/{len(journalists)}] 👤 {journalist['name'][:50]}")
                print(f"🔗 {journalist['url']}")
                print(f"💾 {clickable}")
                
                # Scrape
                data = scraper.scrape_journalist(journalist)
                
                # Save
                saved_path = save_journalist_data(journalist, data)
                print(f"✅ Saved: file://{quote(str(saved_path.absolute()))}")
                
                elapsed = time.time() - start
                tracker.update(scraped=1, elapsed=elapsed)
                checkpoint_urls.add(journalist['url'])
                
                # Checkpoint every 10
                if tracker.scraped % 10 == 0:
                    save_checkpoint(location_name, checkpoint_urls)
                
                # Progress every 5
                if idx % 5 == 0:
                    tracker.print_status()
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                failed_path = save_failed(journalist, e)
                print(f"📝 Failed: file://{quote(str(failed_path.absolute()))}")
                tracker.update(failed=1)
                
            finally:
                scraper.cleanup()
        
        save_checkpoint(location_name, checkpoint_urls)
        logger.info(f"\n✅ Location '{location_name}' complete!")
        tracker.print_status()
    
    # Final summary
    print("\n" + "="*80)
    print("🎉 SCRAPING COMPLETE!")
    print("="*80)
    print(f"✅ Scraped: {tracker.scraped:,}")
    print(f"❌ Failed: {tracker.failed:,}")
    print(f"⏭️ Skipped: {tracker.skipped:,}")
    print(f"⏰ Total time: {tracker.get_stats()['elapsed']}")
    print(f"📁 Data: file://{DATA_DIR.absolute()}")
    print(f"📁 Failed: file://{FAILED_DIR.absolute()}")
    print(f"📋 Log: file://{log_file.absolute()}")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info('\n⏹️ Stopped. Progress saved. Resume by running again.')
