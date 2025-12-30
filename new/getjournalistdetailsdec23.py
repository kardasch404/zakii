#!/usr/bin/env python3
"""Fast Selenium scraper inspired by working JS version"""
import json
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SECTIONS = ['profile', 'portfolio', 'bio', 'awards', 'interviews']
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
LOG_DIR = BASE_DIR / 'logs'
CHECKPOINT_DIR = BASE_DIR / 'checkpoints'

LOG_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file)]
)
logger = logging.getLogger(__name__)

def get_random_user_agent():
    """Get random user agent like JS version"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    ]
    return random.choice(agents)

class JournalistScraper:
    def __init__(self, location_name: str):
        self.location = location_name
        self.driver = None
        self.checkpoint_file = CHECKPOINT_DIR / f'{location_name}_checkpoint.json'
        self.stats = {'total': 0, 'completed': 0, 'failed': 0, 'skipped': 0}
        self.start_time = None
        self.journalist_times = []
    
    def init_driver(self):
        """Create new browser session like JS version"""
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
        """Navigate with retries like JS version"""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"      🔄 Attempt {attempt}/{max_retries} loading {url}")
                
                if attempt > 1:
                    self.driver.delete_all_cookies()
                    time.sleep(2)
                
                self.driver.get(url)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Check if content loaded
                html = self.driver.page_source
                if 'mr-card-content' in html:
                    logger.info(f"      ✅ Successfully loaded {url}")
                    return True
                
                # Check for blocking
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
    
    def prepend_base_url(self, link: str) -> str:
        """Prepend base URL like JS version"""
        if not link:
            return ''
        if link.startswith('http'):
            return link
        return f'https://muckrack.com{link}'
    
    def extract_profile_details(self) -> dict:
        """Extract profile like JS version"""
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
        
        # As seen in - Get ALL including hidden ones
        as_seen = []
        # Get visible ones
        for item in container.select('div.profile-details-item a'):
            as_seen.append({
                'name': item.get_text(strip=True),
                'link': self.prepend_base_url(item.get('href', ''))
            })
        # Get hidden ones from js-as-seen-in-hidden span
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
        
        # Social handles
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
    
    def extract_portfolio(self, journalist_id: str) -> list:
        """Extract portfolio articles"""
        portfolio_url = f'https://muckrack.com/{journalist_id}/portfolio'
        
        if not self.try_navigate_with_retry(portfolio_url):
            return []
        
        time.sleep(1)
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        articles = []
        
        for item in soup.select('div.portfolio-item-container'):
            article = {}
            
            if h3 := item.select_one('h3.portfolio-item-title'):
                article['title'] = h3.get_text(strip=True)
            
            if link := item.select_one('a.portfolio-item-hover'):
                article['link'] = link.get('href', '')
            
            if date := item.select_one('span.date'):
                article['date'] = date.get_text(strip=True)
            
            if desc := item.select_one('div.preview-contents p'):
                article['description'] = desc.get_text(strip=True)
            
            if img := item.select_one('img'):
                article['image'] = img.get('src', '')
            
            # Get outlet from sprite class
            if pub := item.select_one('div.portfolio-item-publication a'):
                for cls in pub.get('class', []):
                    if 'sprite-group-thumbnails-' in cls:
                        article['outlet'] = cls.replace('sprite-group-thumbnails-', '').title()
                        break
            
            if article.get('title'):
                articles.append(article)
        
        logger.info(f"      📰 Found {len(articles)} portfolio articles")
        return articles
    
    def extract_awards(self, journalist_id: str) -> list:
        """Extract awards"""
        awards_url = f'https://muckrack.com/{journalist_id}/awards'
        
        if not self.try_navigate_with_retry(awards_url):
            return []
        
        time.sleep(1)
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        awards = []
        
        for item in soup.select('div.profile-award'):
            award = {}
            
            if h4 := item.select_one('h4.item-header'):
                award['title'] = h4.get_text(strip=True)
            
            if h5 := item.select_one('h5'):
                text = h5.get_text(strip=True)
                parts = text.split('-', 1)
                award['year'] = parts[0].strip() if len(parts) >= 1 else ''
                award['award_name'] = parts[1].strip() if len(parts) == 2 else ''
            
            if desc := item.select_one('p.mt-4'):
                award['description'] = desc.get_text(strip=True)
            
            if award:
                awards.append(award)
        
        logger.info(f"      🏆 Found {len(awards)} awards")
        return awards
    
    def extract_interviews(self, journalist_id: str) -> list:
        """Extract interview Q&A"""
        interview_url = f'https://muckrack.com/{journalist_id}/interview'
        
        if not self.try_navigate_with_retry(interview_url):
            return []
        
        time.sleep(1)
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        interviews = []
        
        for item in soup.select('div.profile-interview-answer'):
            interview = {}
            
            if h4 := item.select_one('h4'):
                interview['question'] = h4.get_text(strip=True)
            
            if answer := item.select_one('div.interview-answer'):
                interview['answer'] = answer.get_text(strip=True)
            
            if interview:
                interviews.append(interview)
        
        logger.info(f"      💬 Found {len(interviews)} interview Q&As")
        return interviews
    
    def extract_biography(self, journalist_id: str) -> str:
        """Extract biography like JS version"""
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        bio_div = soup.select_one('div.profile-section.profile-bio')
        if not bio_div:
            return ''
        
        # Check for full bio link
        full_bio_link = bio_div.select_one('a[href$="/bio"]')
        bio_text = '\n\n'.join([p.get_text(strip=True) for p in bio_div.select('div.mr-card-content p') if p.get_text(strip=True)])
        
        if full_bio_link:
            expected_link = f'/{journalist_id}/bio'
            actual_link = full_bio_link.get('href', '')
            
            if actual_link == expected_link:
                logger.info(f"      📖 Found 'Read Full Bio' link: {actual_link}")
                full_bio_url = self.prepend_base_url(actual_link)
                
                if self.try_navigate_with_retry(full_bio_url):
                    time.sleep(1)
                    soup = BeautifulSoup(self.driver.page_source, 'lxml')
                    if full_bio_div := soup.select_one('div.profile-section.profile-bio'):
                        bio_text = '\n\n'.join([p.get_text(strip=True) for p in full_bio_div.select('div.mr-card-content p') if p.get_text(strip=True)])
                        logger.info(f"      ✅ Extracted full bio: {bio_text[:50]}...")
                else:
                    logger.error(f"      ❌ Failed to navigate to full bio: {full_bio_url}")
        else:
            logger.info("      ℹ️ No 'Read Full Bio' link found, using truncated bio")
        
        return bio_text
    
    def get_missing_sections(self, name: str) -> Set[str]:
        """Check what sections are missing"""
        data_file = DATA_DIR / self.location / name / f'{name}.json'
        existing = set()
        if data_file.exists():
            try:
                data = json.loads(data_file.read_text())
                if data.get('profile') and data['profile'].get('name'):
                    existing.add('profile')
                if data.get('biography') and data['biography'].strip():
                    existing.add('bio')
                if data.get('portfolio') and len(data['portfolio']) > 0:
                    existing.add('portfolio')
                if data.get('awards') and len(data['awards']) > 0:
                    existing.add('awards')
                if data.get('interviews') and len(data['interviews']) > 0:
                    existing.add('interviews')
            except:
                pass
        return set(SECTIONS) - existing
    
    def scrape_journalist(self, journalist: Dict) -> bool:
        """Scrape journalist details like JS version"""
        name = journalist['name']
        url = journalist['link']
        journalist_id = url.split('/')[-1]
        
        missing = self.get_missing_sections(name)
        if not missing:
            self.stats['skipped'] += 1
            logger.info(f"      ⏭️  Skipping already processed: {name}")
            return True
        
        try:
            start_time = time.time()
            logger.info(f"      📄 Scraping: {name} ({url})")
            
            # Create new browser for each journalist
            self.init_driver()
            
            if not self.try_navigate_with_retry(url):
                logger.error(f"      ❌ Failed to load page for {name}")
                raise Exception('Navigation failed')
            
            details = {
                'url': url,
                'profile': self.extract_profile_details(),
                'biography': self.extract_biography(journalist_id),
                'portfolio': self.extract_portfolio(journalist_id),
                'awards': self.extract_awards(journalist_id),
                'interviews': self.extract_interviews(journalist_id),
                'scraped_at': datetime.now().isoformat()
            }
            
            # Save
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
        """Load progress"""
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
        """Save progress"""
        data = {
            'location': self.location,
            'completed': list(completed),
            'last_updated': datetime.now().isoformat(),
            'stats': self.stats
        }
        self.checkpoint_file.write_text(json.dumps(data, indent=2))
        logger.info(f"💾 Checkpoint saved: {len(completed)} completed")
    
    def process_location(self, journalists: List[Dict]):
        """Process all journalists with resume functionality"""
        completed = self.load_checkpoint()
        self.stats['total'] = len(journalists)
        self.start_time = time.time()
        
        # Filter remaining
        remaining = [j for j in journalists if j['name'] not in completed]
        
        if not remaining:
            logger.info(f"✅ All journalists for {self.location} have already been processed!")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📍 LOCATION: {self.location}")
        logger.info(f"📊 Total: {len(journalists)} | Completed: {len(completed)} | Remaining: {len(remaining)}")
        logger.info(f"{'='*80}\n")
        
        for i, journalist in enumerate(remaining, 1):
            # Progress header
            logger.info(f"\n━━━ [{i}/{len(remaining)}] {journalist['name']} ━━━")
            
            try:
                success = self.scrape_journalist(journalist)
                if success:
                    completed.add(journalist['name'])
                    
                    # Calculate stats
                    total_completed = len(completed)
                    elapsed = time.time() - self.start_time
                    avg_time = sum(self.journalist_times) / len(self.journalist_times) if self.journalist_times else 0
                    remaining_count = len(journalists) - total_completed
                    eta_seconds = avg_time * remaining_count
                    success_rate = (self.stats['completed'] / (self.stats['completed'] + self.stats['failed']) * 100) if (self.stats['completed'] + self.stats['failed']) > 0 else 0
                    
                    # Progress summary every journalist
                    logger.info(f"\n📊 PROGRESS: {total_completed}/{len(journalists)} ({total_completed/len(journalists)*100:.1f}%)")
                    logger.info(f"✅ Success: {self.stats['completed']} | ❌ Failed: {self.stats['failed']} | ⏭️ Skipped: {self.stats['skipped']}")
                    logger.info(f"⏱️  Avg: {avg_time:.1f}s/journalist | ETA: {str(timedelta(seconds=int(eta_seconds)))}")
                    logger.info(f"📈 Success Rate: {success_rate:.1f}%")
                    
                    # Save every 5 journalists
                    if i % 5 == 0:
                        self.save_checkpoint(completed)
                        logger.info(f"💾 Checkpoint saved")
                
            except Exception as e:
                logger.error(f"❌ Unexpected error: {str(e)[:100]}")
                self.stats['failed'] += 1
            
            # Delay between journalists (3 seconds)
            if i < len(remaining):
                logger.info(f"⏳ Delay: 3s\n")
                time.sleep(3)
        
        # Final save
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
    logger.info(f"🌍 MUCK RACK JOURNALIST SCRAPER")
    logger.info(f"📊 Total: {total:,} journalists across {len(all_locations)} locations")
    logger.info(f"{'='*80}\n")
    
    global_start = time.time()
    global_stats = {'completed': 0, 'failed': 0, 'skipped': 0}
    
    for idx, location_dir in enumerate(all_locations, 1):
        logger.info(f"\n🔹 [{idx}/{len(all_locations)}] Processing: {location_dir.name}")
        
        scraper = JournalistScraper(location_dir.name)
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
    
    # Final global summary
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
