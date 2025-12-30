#!/usr/bin/env python3
"""Profile-only scraper - Skip bio, portfolio, awards, interviews"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SECTIONS = ['profile']
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
LOG_DIR = BASE_DIR / 'logs'
CHECKPOINT_DIR = BASE_DIR / 'checkpoints'

LOG_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f'profile_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file)]
)
logger = logging.getLogger(__name__)

def get_random_user_agent():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    return random.choice(agents)

class ProfileScraper:
    def __init__(self, location_name: str):
        self.location = location_name
        self.driver = None
        self.checkpoint_file = CHECKPOINT_DIR / f'{location_name}_profile_checkpoint.json'
        self.stats = {'total': 0, 'completed': 0, 'failed': 0, 'skipped': 0}
        self.start_time = None
        self.journalist_times = []
    
    def init_driver(self):
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
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-site-isolation-trials')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={get_random_user_agent()}')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        logger.info("🚗 Browser session created")
    
    def try_navigate_with_retry(self, url: str, max_retries: int = 3) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"      🔄 Attempt {attempt}/{max_retries} loading {url}")
                
                if attempt > 1:
                    self.driver.delete_all_cookies()
                    time.sleep(2)
                
                self.driver.get(url)
                time.sleep(random.uniform(0.5, 1.0))
                
                html = self.driver.page_source
                if 'mr-card-content' in html:
                    logger.info(f"      ✅ Successfully loaded {url}")
                    return True
                
                if any(x in html.lower() for x in ['security check', 'captcha', 'blocked', 'just a moment']):
                    logger.warning("      ⚠️ Detected potential blocking, rotating session...")
                    self.init_driver()
                    if attempt < max_retries:
                        time.sleep(2)
                
            except Exception as e:
                logger.warning(f"      ⚠️ Navigation error on attempt {attempt}: {str(e)[:50]}")
                if attempt == max_retries:
                    raise
                time.sleep(2)
        
        logger.error(f"      ❌ Failed to load {url} after {max_retries} attempts")
        return False
    
    def extract_profile_details(self) -> dict:
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        intro = soup.select_one('div.profile-section.profile-intro')
        if not intro:
            return {}
        c = intro.select_one('div.mr-card-content')
        if not c:
            return {}
        
        pronouns = ''
        if p := c.select_one('div.fs-6.text-muted.fw-light'):
            pronouns = p.get_text(strip=True)
        
        intro_text = ''
        if desc := c.select_one('div.fs-5.fs-md-6.my-5'):
            intro_text = desc.get_text(strip=True)
        
        jobs = []
        for li in c.select('ul.mr-person-job-items li'):
            text = li.get_text(strip=True).replace('\uf1ad', '').strip()
            a = li.select_one('a')
            if ',' in text and a:
                title = text.split(',')[0].strip()
                href = a.get('href', '')
                full_url = href if href.startswith('http') else f"https://muckrack.com{href}"
                jobs.append({'title': title, 'outlet': a.get_text(strip=True), 'outletLink': full_url})
        
        covers = doesnt_cover = ''
        for item in c.select('div.profile-details-item'):
            txt = item.get_text()
            if 'Covers:' in txt:
                covers = txt.split('Covers:', 1)[1].strip()
            elif "Doesn't Cover:" in txt:
                doesnt_cover = txt.split("Doesn't Cover:", 1)[1].strip()
        
        return {
            'avatar': (img.get('src', '') if (img := c.select_one('img[src*="profile/images"]')) else ''),
            'name': (h1.get_text(strip=True) if (h1 := c.select_one('h1.profile-name')) else ''),
            'pronouns': pronouns,
            'verified': bool(c.select_one('small.profile-verified')),
            'jobs': jobs,
            'location': (s.get_text(strip=True) if (s := c.select_one('div.person-details-location span')) else ''),
            'beats': [{'name': a.get_text(strip=True), 'link': f"https://muckrack.com{a.get('href', '')}"} for a in c.select('div.person-details-beats a')],
            'asSeenIn': [{'name': a.get_text(strip=True), 'link': f"https://muckrack.com{a.get('href', '')}"} for a in c.select('div.profile-details-item a')],
            'socialHandles': [{'handle': a.get_text(strip=True), 'link': a.get('href', '')} for a in c.select('a.tweet-url.username')],
            'covers': covers,
            'doesnt_cover': doesnt_cover,
            'intro': intro_text
        }
    
    def get_missing_sections(self, name: str) -> Set[str]:
        data_file = DATA_DIR / self.location / name / f'{name}.json'
        existing = set()
        if data_file.exists():
            try:
                data = json.loads(data_file.read_text())
                profile = data.get('profile', {})
                # Check if profile has NEW fields
                if profile.get('name') and 'pronouns' in profile and 'intro' in profile and 'doesnt_cover' in profile:
                    existing.add('profile')
            except:
                pass
        return set(SECTIONS) - existing
    
    def scrape_journalist(self, journalist: Dict) -> bool:
        name = journalist['name']
        url = journalist['link']
        
        missing = self.get_missing_sections(name)
        if not missing:
            self.stats['skipped'] += 1
            logger.info(f"      ⏭️  Skipping already processed: {name}")
            return True
        
        try:
            start_time = time.time()
            logger.info(f"      📄 Scraping: {name} ({url})")
            
            self.init_driver()
            
            if not self.try_navigate_with_retry(url):
                logger.error(f"      ❌ Failed to load page for {name}")
                raise Exception('Navigation failed')
            
            details = {
                'url': url,
                'profile': self.extract_profile_details(),
                'scraped_at': datetime.now().isoformat()
            }
            
            dir_path = DATA_DIR / self.location / name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            file_path = dir_path / f'{name}.json'
            file_path.write_text(json.dumps(details, indent=2, ensure_ascii=False))
            
            elapsed = time.time() - start_time
            self.journalist_times.append(elapsed)
            
            logger.info(f"      ✅ Saved {name} ({elapsed:.1f}s)")
            self.stats['completed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"      ❌ Error scraping {name}: {str(e)[:100]}")
            self.stats['failed'] += 1
            return False
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                except:
                    pass
    
    def load_checkpoint(self) -> Set[str]:
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text())
                completed = set(data.get('completed', []))
                logger.info(f"📂 Loaded checkpoint: {len(completed)} journalists completed")
                return completed
            except:
                pass
        return set()
    
    def save_checkpoint(self, completed: Set[str]):
        data = {
            'location': self.location,
            'completed': list(completed),
            'last_updated': datetime.now().isoformat(),
            'stats': self.stats
        }
        self.checkpoint_file.write_text(json.dumps(data, indent=2))
        logger.info(f"💾 Checkpoint saved: {len(completed)} completed")
    
    def process_location(self, journalists: List[Dict]):
        completed = self.load_checkpoint()
        self.stats['total'] = len(journalists)
        self.start_time = time.time()
        
        remaining = [j for j in journalists if j['name'] not in completed]
        
        if not remaining:
            logger.info(f"✅ All journalists for {self.location} have already been processed!")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📍 LOCATION: {self.location}")
        logger.info(f"📊 Total: {len(journalists)} | Completed: {len(completed)} | Remaining: {len(remaining)}")
        logger.info(f"{'='*80}\n")
        
        for i, journalist in enumerate(remaining, 1):
            logger.info(f"\n━━━ [{i}/{len(remaining)}] {journalist['name']} ━━━")
            
            try:
                success = self.scrape_journalist(journalist)
                if success:
                    completed.add(journalist['name'])
                    
                    total_completed = len(completed)
                    elapsed = time.time() - self.start_time
                    avg_time = sum(self.journalist_times) / len(self.journalist_times) if self.journalist_times else 0
                    remaining_count = len(journalists) - total_completed
                    eta_seconds = avg_time * remaining_count
                    success_rate = (self.stats['completed'] / (self.stats['completed'] + self.stats['failed']) * 100) if (self.stats['completed'] + self.stats['failed']) > 0 else 0
                    
                    logger.info(f"\n📊 PROGRESS: {total_completed}/{len(journalists)} ({total_completed/len(journalists)*100:.1f}%)")
                    logger.info(f"✅ Success: {self.stats['completed']} | ❌ Failed: {self.stats['failed']} | ⏭️ Skipped: {self.stats['skipped']}")
                    logger.info(f"⏱️  Avg: {avg_time:.1f}s/journalist | ETA: {str(timedelta(seconds=int(eta_seconds)))}")
                    logger.info(f"📈 Success Rate: {success_rate:.1f}%")
                    
                    if i % 5 == 0:
                        self.save_checkpoint(completed)
                        logger.info(f"💾 Checkpoint saved")
                
            except Exception as e:
                logger.error(f"❌ Unexpected error: {str(e)[:100]}")
                self.stats['failed'] += 1
            
            if i < len(remaining):
                logger.info(f"⏳ Delay: 3s\n")
                time.sleep(3)
        
        self.save_checkpoint(completed)
        
        elapsed = time.time() - self.start_time
        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 LOCATION COMPLETE: {self.location}")
        logger.info(f"⏱️  Time: {str(timedelta(seconds=int(elapsed)))}")
        logger.info(f"✅ Success: {self.stats['completed']} | ❌ Failed: {self.stats['failed']} | ⏭️ Skipped: {self.stats['skipped']}")
        logger.info(f"📊 Total: {len(journalists)}")
        logger.info(f"{'='*80}\n")

def main():
    all_locations = sorted([d for d in DATA_DIR.glob('*') if d.is_dir()])
    total = sum(len([d for d in loc.glob('*') if d.is_dir()]) for loc in all_locations)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🌍 PROFILE-ONLY SCRAPER")
    logger.info(f"📊 Total: {total:,} journalists across {len(all_locations)} locations")
    logger.info(f"{'='*80}\n")
    
    global_start = time.time()
    global_stats = {'completed': 0, 'failed': 0, 'skipped': 0}
    
    for idx, location_dir in enumerate(all_locations, 1):
        logger.info(f"\n🔹 [{idx}/{len(all_locations)}] Processing: {location_dir.name}")
        
        scraper = ProfileScraper(location_dir.name)
        journalists = []
        
        for journalist_dir in location_dir.glob('*'):
            if not journalist_dir.is_dir():
                continue
            json_file = journalist_dir / f'{journalist_dir.name}.json'
            if json_file.exists():
                try:
                    data = json.loads(json_file.read_text())
                    url = data.get('url') or data.get('link')
                    if url:
                        journalists.append({'name': journalist_dir.name, 'link': url})
                except:
                    pass
        
        if journalists:
            scraper.process_location(journalists)
            global_stats['completed'] += scraper.stats['completed']
            global_stats['failed'] += scraper.stats['failed']
            global_stats['skipped'] += scraper.stats['skipped']
    
    global_elapsed = time.time() - global_start
    logger.info(f"\n{'='*80}")
    logger.info(f"🎆 ALL LOCATIONS COMPLETE!")
    logger.info(f"⏱️  Total Time: {str(timedelta(seconds=int(global_elapsed)))}")
    logger.info(f"✅ Success: {global_stats['completed']:,} | ❌ Failed: {global_stats['failed']:,} | ⏭️ Skipped: {global_stats['skipped']:,}")
    logger.info(f"📊 Total Processed: {sum(global_stats.values()):,}")
    logger.info(f"{'='*80}\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('\n⏹️ Received shutdown signal. Progress has been saved.')
        logger.info('💡 You can resume by running the script again.')
