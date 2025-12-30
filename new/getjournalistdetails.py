#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

SECTIONS = ['profile', 'portfolio', 'bio', 'awards', 'interviews']
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
FAILED_DIR = BASE_DIR / 'muckrack' / 'failed'
LOG_DIR = BASE_DIR / 'logs'
CHECKPOINT_DIR = BASE_DIR / 'checkpoints'

LOG_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(), file_handler]
)
logger = logging.getLogger(__name__)

class JournalistScraper:
    def __init__(self, location_name: str):
        self.location = location_name
        self.driver = None
        self.request_count = 0
        self.checkpoint_file = CHECKPOINT_DIR / f'{location_name}_checkpoint.json'
        self.stats = {'total': 0, 'completed': 0, 'failed': 0, 'skipped': 0}
        self.consecutive_failures = 0
    
    def load_checkpoint(self) -> Set[str]:
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text())
                completed = set(data.get('completed', []))
                logger.info(f"📋 Checkpoint: {len(completed)} completed")
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
    
    def log_stats(self):
        logger.info(f"📊 {self.stats['completed']}/{self.stats['total']} done, "
                   f"{self.stats['failed']} failed, {self.stats['skipped']} skipped")
    
    def get_missing_sections(self, name: str) -> Set[str]:
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
    
    def init_driver(self):
        """Initialize Selenium with stealth mode to avoid detection"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        try:
            options = Options()
            
            # Essential options
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # Randomize user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            # Additional stealth options
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-extensions')
            options.add_argument('--profile-directory=Default')
            options.add_argument('--incognito')
            options.add_argument('--disable-plugins-discovery')
            options.add_argument('--start-maximized')
            
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            }
            options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=options)
            
            # Apply stealth techniques
            stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            
            logger.info("🚗 Selenium initialized with stealth mode")
            
        except Exception as e:
            logger.error(f"❌ Driver init failed: {e}")
            self.driver = None
    
    def human_like_scroll(self):
        """Simulate human-like scrolling behavior"""
        try:
            # Random scroll patterns
            scroll_actions = [
                "window.scrollTo(0, 300);",
                "window.scrollTo(0, 500);",
                "window.scrollTo(0, 800);",
                "window.scrollTo(0, document.body.scrollHeight/2);",
                "window.scrollTo(0, document.body.scrollHeight/3);",
                "window.scrollTo(0, 100);",
            ]
            
            for _ in range(random.randint(2, 4)):
                self.driver.execute_script(random.choice(scroll_actions))
                time.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            logger.debug(f"Scroll error: {e}")
    
    def fetch_page(self, url: str, wait_    for_selector: str = None) -> str:
        """Fetch page with human-like behavior"""
        try:
            # Reinitialize driver periodically
            if self.request_count % 10 == 0 or not self.driver:
                logger.info("🔄 Refreshing browser...")
                self.init_driver()
                if not self.driver:
                    return None
            
            self.request_count += 1
            
            logger.info(f"🌐 Fetching: {url}")
            self.driver.get(url)
            
            # Initial wait - mimic human reading time
            wait_time = random.uniform(5, 8)
            logger.info(f"⏳ Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            
            # Human-like scrolling
            self.human_like_scroll()
            
            # Check for Cloudflare challenge
            html = self.driver.page_source
            
            if 'Just a moment' in html or 'Checking your browser' in html or 'cf-browser-verification' in html:
                logger.warning("⚠️ Cloudflare detected, waiting...")
                
                # Wait for Cloudflare to complete (30-45 seconds)
                wait = random.uniform(30, 45)
                logger.info(f"⏳ Cloudflare wait: {wait:.1f}s")
                time.sleep(wait)
                
                # Scroll again
                self.human_like_scroll()
                
                html = self.driver.page_source
                
                # If still blocked, wait even longer
                if 'Just a moment' in html:
                    logger.warning("⚠️ Still blocked, extended wait...")
                    time.sleep(random.uniform(30, 45))
                    html = self.driver.page_source
            
            # Wait for specific content if selector provided
            if wait_for_selector:
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                except Exception as e:
                    logger.debug(f"Element wait timeout: {e}")
            
            # Final check
            if 'Just a moment' in html or len(html) < 5000:
                logger.warning("⚠️ Page may not be fully loaded")
                return None
            
            return html
            
        except Exception as e:
            logger.error(f"❌ Fetch error: {str(e)[:100]}")
            return None
    
    def parse_profile(self, soup):
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
    
    def parse_bio(self, soup):
        bio_div = soup.select_one('div.profile-section.profile-bio div.mr-card-content')
        if not bio_div:
            return ''
        paragraphs = [p.get_text(strip=True) for p in bio_div.select('p') if p.get_text(strip=True)]
        return '\n\n'.join(paragraphs)
    
    def parse_articles(self, soup):
        articles = []
        for item in soup.select('div.portfolio-item-container'):
            article = {}
            if h3 := item.select_one('h3.portfolio-item-title'):
                article['title'] = h3.get_text(strip=True)
            if link := item.select_one('a.portfolio-item-hover'):
                article['link'] = link.get('href', '')
            if date_span := item.select_one('span.date'):
                article['date'] = date_span.get_text(strip=True)
            else:
                article['date'] = ''
            if p := item.select_one('div.preview-contents p'):
                article['description'] = p.get_text(strip=True)
            else:
                article['description'] = ''
            if img := item.select_one('img'):
                article['image'] = img.get('src', '')
            else:
                article['image'] = ''
            article['outlet'] = ''
            if pub_div := item.select_one('div.portfolio-item-publication a'):
                classes = pub_div.get('class', [])
                for cls in classes:
                    if 'sprite-group-thumbnails-' in cls:
                        article['outlet'] = cls.replace('sprite-group-thumbnails-', '').title()
                        break
            if article.get('title'):
                articles.append(article)
        return articles
    
    def parse_awards(self, soup):
        awards = []
        for item in soup.select('div.profile-award'):
            award = {}
            if h4 := item.select_one('h4.item-header'):
                award['title'] = h4.get_text(strip=True)
            if h5 := item.select_one('h5'):
                text = h5.get_text(strip=True)
                parts = text.split('-', 1)
                if len(parts) == 2:
                    award['year'] = parts[0].strip()
                    award['award_name'] = parts[1].strip()
                else:
                    award['year'] = text
                    award['award_name'] = ''
            if p := item.select_one('p.mt-4'):
                award['description'] = p.get_text(strip=True)
            else:
                award['description'] = ''
            if award:
                awards.append(award)
        return awards
    
    def parse_interviews(self, soup):
        interviews = []
        for item in soup.select('div.profile-interview-answer'):
            interview = {}
            if h4 := item.select_one('h4'):
                interview['question'] = h4.get_text(strip=True)
            if answer_div := item.select_one('div.interview-answer'):
                interview['answer'] = answer_div.get_text(strip=True)
            if interview:
                interviews.append(interview)
        return interviews
    
    def scrape_journalist(self, journalist: Dict) -> bool:
        name = journalist['name']
        url = journalist['link']
        journalist_id = url.split('/')[-1]
        
        missing = self.get_missing_sections(name)
        if not missing:
            logger.info(f"✅ {name}: Complete")
            self.stats['skipped'] += 1
            return True
        
        logger.info(f"🔄 {name}: Missing {missing}")
        
        data_file = DATA_DIR / self.location / name / f'{name}.json'
        data = json.loads(data_file.read_text()) if data_file.exists() else {'name': name, 'link': url}
        data['url'] = url
        
        try:
            start_time = time.time()
            
            # Fetch main profile
            html = self.fetch_page(url, "div.mr-card-content, h1.profile-name")
            
            if not html:
                raise Exception("Failed to fetch main page")
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Parse sections
            if 'profile' in missing:
                data['profile'] = self.parse_profile(soup)
            
            if 'bio' in missing:
                bio = self.parse_bio(soup)
                if not bio or len(bio) < 100:
                    time.sleep(random.uniform(3, 6))
                    bio_html = self.fetch_page(f'https://muckrack.com/{journalist_id}/bio')
                    if bio_html:
                        full_bio = self.parse_bio(BeautifulSoup(bio_html, 'lxml'))
                        if full_bio:
                            bio = full_bio
                data['biography'] = bio
            
            if 'portfolio' in missing:
                time.sleep(random.uniform(3, 6))
                port_html = self.fetch_page(f'https://muckrack.com/{journalist_id}/portfolio')
                if port_html:
                    data['portfolio'] = self.parse_articles(BeautifulSoup(port_html, 'lxml'))
                    data['portfolio_count'] = len(data['portfolio'])
            
            if 'awards' in missing:
                time.sleep(random.uniform(3, 6))
                award_html = self.fetch_page(f'https://muckrack.com/{journalist_id}/awards')
                if award_html:
                    data['awards'] = self.parse_awards(BeautifulSoup(award_html, 'lxml'))
            
            if 'interviews' in missing:
                time.sleep(random.uniform(3, 6))
                int_html = self.fetch_page(f'https://muckrack.com/{journalist_id}/interview')
                if int_html:
                    data['interviews'] = self.parse_interviews(BeautifulSoup(int_html, 'lxml'))
            
            # Set defaults
            data.setdefault('profile', {})
            data.setdefault('biography', '')
            data.setdefault('portfolio', [])
            data.setdefault('portfolio_count', len(data.get('portfolio', [])))
            data.setdefault('awards', [])
            data.setdefault('interviews', [])
            data['scraped_at'] = datetime.now().isoformat()
            
            # Save
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            
            elapsed = time.time() - start_time
            logger.info(f"✅ {name}: Done in {elapsed:.1f}s")
            self.stats['completed'] += 1
            self.consecutive_failures = 0
            return True
            
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            self._save_failed(name, url, str(e))
            self.stats['failed'] += 1
            self.consecutive_failures += 1
            
            # If too many consecutive failures, take longer break
            if self.consecutive_failures >= 3:
                logger.warning(f"⚠️ {self.consecutive_failures} consecutive failures, taking longer break...")
                time.sleep(random.uniform(60, 90))
                self.consecutive_failures = 0
            
            return False
    
    def _save_failed(self, name: str, url: str, error: str):
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        failed_file = FAILED_DIR / f"{self.location}_failed.json"
        failed_data = json.loads(failed_file.read_text()) if failed_file.exists() else []
        failed_data.append({'name': name, 'url': url, 'error': error, 'timestamp': datetime.now().isoformat()})
        failed_file.write_text(json.dumps(failed_data, indent=2, ensure_ascii=False))
    
    def process_location(self, journalists: List[Dict]):
        completed = self.load_checkpoint()
        self.stats['total'] = len(journalists)
        
        remaining = [j for j in journalists if j['name'] not in completed]
        
        logger.info(f"🚀 {self.location}: {len(journalists)} total, {len(remaining)} remaining")
        
        if not remaining:
            logger.info(f"✅ All complete!")
            return
        
        start_time = time.time()
        
        for i, j in enumerate(remaining, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📦 {i}/{len(remaining)} (Total: {len(completed) + i}/{len(journalists)})")
            
            try:
                success = self.scrape_journalist(j)
                
                if success:
                    completed.add(j['name'])
                    
                    # Save checkpoint every journalist
                    if i % 3 == 0:
                        self.save_checkpoint(completed)
                        self.log_stats()
                
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                self.stats['failed'] += 1
            
            # Smart delays based on progress
            if i % 10 == 0:
                delay = random.uniform(30, 45)  # Longer break every 10
                logger.info(f"☕ Long break: {delay:.1f}s")
            elif i % 5 == 0:
                delay = random.uniform(15, 25)  # Medium break every 5
                logger.info(f"☕ Medium break: {delay:.1f}s")
            else:
                delay = random.uniform(8, 15)  # Short delay between requests
                logger.info(f"⏸️ Short delay: {delay:.1f}s")
            
            time.sleep(delay)
        
        self.save_checkpoint(completed)
        
        elapsed = time.time() - start_time
        logger.info(f"\n🎉 {self.location} done in {elapsed/60:.1f} minutes!")
        self.log_stats()
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def main():
    for location_dir in DATA_DIR.glob('*'):
        if not location_dir.is_dir():
            continue
        
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
            logger.info(f"📍 {location_dir.name}: {len(journalists)} journalists")
            scraper.process_location(journalists)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('\n⏹️ Stopped by user')