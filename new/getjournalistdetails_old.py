#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import time
import random
import cloudscraper
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SECTIONS = ['profile', 'portfolio', 'bio', 'awards', 'interviews']
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
FAILED_DIR = BASE_DIR / 'muckrack' / 'failed'
LOG_DIR = Path('logs')

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class JournalistScraper:
    def __init__(self, location_name: str):
        self.location = location_name
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'linux', 'mobile': False}
        )
        self.driver = None
        self.request_count = 0
        self.last_request_time = 0
    
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
    
    def fetch_with_cloudscraper(self, url: str) -> str:
        try:
            # Adaptive delay based on request count
            now = time.time()
            if self.last_request_time:
                elapsed = now - self.last_request_time
                if elapsed < 2:
                    time.sleep(random.uniform(1, 3))
            
            self.request_count += 1
            self.last_request_time = now
            
            # Rotate user agents every 10 requests
            if self.request_count % 10 == 0:
                self.scraper = cloudscraper.create_scraper(
                    browser={'browser': 'chrome', 'platform': 'linux', 'mobile': False}
                )
            
            resp = self.scraper.get(url, timeout=15)
            if resp.status_code == 200:
                html = resp.text
                if 'cloudflare' not in html.lower() and ('mr-card' in html or 'profile-' in html):
                    return html
        except:
            pass
        return None
    
    def init_driver(self):
        if not self.driver:
            try:
                options = Options()
                options.add_argument('--headless=new')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                options.add_argument('--accept-language=en-US,en;q=0.9')
                options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                options.add_experimental_option('useAutomationExtension', False)
                prefs = {"profile.default_content_setting_values.notifications": 2}
                options.add_experimental_option("prefs", prefs)
                
                self.driver = webdriver.Chrome(options=options)
                
                # Advanced stealth
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
                self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
                
                logger.info("🚗 Selenium driver initialized")
            except Exception as e:
                logger.error(f"❌ Driver init failed: {e}")
                self.driver = None
    
    def fetch_with_selenium(self, url: str) -> str:
        try:
            self.init_driver()
            if not self.driver:
                return None
            
            self.driver.get(url)
            
            # Variable wait times - unpredictable pattern
            wait_time = random.choice([2, 3, 4, 5, 6])
            time.sleep(wait_time)
            
            # Random human actions
            actions = [
                lambda: self.driver.execute_script("window.scrollTo(0, 300);"),
                lambda: self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);"),
                lambda: self.driver.execute_script("window.scrollTo(0, 100);"),
            ]
            random.choice(actions)()
            time.sleep(random.uniform(0.3, 0.8))
            
            # Wait for content
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.mr-card-content, h1.profile-name, div.profile-section"))
                )
            except:
                pass
            
            html = self.driver.page_source
            
            # If Cloudflare detected, wait longer with random pattern
            if 'Just a moment' in html or 'cf-browser-verification' in html:
                logger.warning("⚠️ Cloudflare detected, waiting...")
                wait_times = [5, 6, 7, 8, 9, 10]
                time.sleep(random.choice(wait_times))
                html = self.driver.page_source
            
            return html
        except Exception as e:
            logger.warning(f"⚠️ Selenium: {str(e)[:80]}")
            return None
    
    def parse_profile(self, soup):
        intro = soup.select_one('div.profile-section.profile-intro')
        if not intro:
            return {}
        c = intro.select_one('div.mr-card-content')
        if not c:
            return {}
        
        # Pronouns
        pronouns = ''
        if p := c.select_one('div.fs-6.text-muted.fw-light'):
            pronouns = p.get_text(strip=True)
        
        # Intro/Bio text
        intro_text = ''
        if desc := c.select_one('div.fs-5.fs-md-6.my-5'):
            intro_text = desc.get_text(strip=True)
        
        # Jobs
        jobs = []
        for li in c.select('ul.mr-person-job-items li'):
            text = li.get_text(strip=True).replace('\uf1ad', '').strip()
            a = li.select_one('a')
            if ',' in text and a:
                title = text.split(',')[0].strip()
                href = a.get('href', '')
                full_url = href if href.startswith('http') else f"https://muckrack.com{href}"
                jobs.append({'title': title, 'outlet': a.get_text(strip=True), 'outletLink': full_url})
        
        # Covers and Doesn't Cover
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
            
            # Title
            if h3 := item.select_one('h3.portfolio-item-title'):
                article['title'] = h3.get_text(strip=True)
            
            # Link
            if link := item.select_one('a.portfolio-item-hover'):
                article['link'] = link.get('href', '')
            
            # Date
            if date_span := item.select_one('span.date'):
                article['date'] = date_span.get_text(strip=True)
            else:
                article['date'] = ''
            
            # Description
            if p := item.select_one('div.preview-contents p'):
                article['description'] = p.get_text(strip=True)
            else:
                article['description'] = ''
            
            # Image
            if img := item.select_one('img'):
                article['image'] = img.get('src', '')
            else:
                article['image'] = ''
            
            # Outlet (from publication div)
            article['outlet'] = ''
            if pub_div := item.select_one('div.portfolio-item-publication a'):
                # Extract outlet from class name
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
            
            # Title (organization)
            if h4 := item.select_one('h4.item-header'):
                award['title'] = h4.get_text(strip=True)
            
            # Year and award name
            if h5 := item.select_one('h5'):
                text = h5.get_text(strip=True)
                parts = text.split('-', 1)
                if len(parts) == 2:
                    award['year'] = parts[0].strip()
                    award['award_name'] = parts[1].strip()
                else:
                    award['year'] = text
                    award['award_name'] = ''
            
            # Description
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
            
            # Question
            if h4 := item.select_one('h4'):
                interview['question'] = h4.get_text(strip=True)
            
            # Answer
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
            return True
        
        logger.info(f"🔄 {name}: {missing}")
        
        data_file = DATA_DIR / self.location / name / f'{name}.json'
        data = json.loads(data_file.read_text()) if data_file.exists() else {'name': name, 'link': url}
        data['url'] = url
        
        try:
            # Try cloudscraper first
            html = self.fetch_with_cloudscraper(url)
            if not html:
                logger.info(f"🛡️ {name}: Using Selenium")
                html = self.fetch_with_selenium(url)
            
            if not html:
                raise Exception("Failed to fetch")
            
            soup = BeautifulSoup(html, 'lxml')
            
            if 'profile' in missing:
                data['profile'] = self.parse_profile(soup)
            
            if 'bio' in missing:
                bio = self.parse_bio(soup)
                if not bio or len(bio) < 100:
                    time.sleep(random.uniform(1, 3))
                    bio_html = self.fetch_with_cloudscraper(f'https://muckrack.com/{journalist_id}/bio')
                    if not bio_html:
                        bio_html = self.fetch_with_selenium(f'https://muckrack.com/{journalist_id}/bio')
                    if bio_html and 'Just a moment' not in bio_html:
                        full_bio = self.parse_bio(BeautifulSoup(bio_html, 'lxml'))
                        if full_bio:
                            bio = full_bio
                data['biography'] = bio
            
            # Portfolio
            if 'portfolio' in missing:
                port_html = self.fetch_with_cloudscraper(f'https://muckrack.com/{journalist_id}/portfolio')
                if not port_html:
                    port_html = self.fetch_with_selenium(f'https://muckrack.com/{journalist_id}/portfolio')
                if port_html:
                    data['portfolio'] = self.parse_articles(BeautifulSoup(port_html, 'lxml'))
                    data['portfolio_count'] = len(data['portfolio'])
            
            # Awards
            if 'awards' in missing:
                award_html = self.fetch_with_cloudscraper(f'https://muckrack.com/{journalist_id}/awards')
                if not award_html:
                    award_html = self.fetch_with_selenium(f'https://muckrack.com/{journalist_id}/awards')
                if award_html:
                    data['awards'] = self.parse_awards(BeautifulSoup(award_html, 'lxml'))
            
            # Interviews - fetch from /interview page (not /interviews)
            if 'interviews' in missing:
                int_html = self.fetch_with_cloudscraper(f'https://muckrack.com/{journalist_id}/interview')
                if not int_html:
                    int_html = self.fetch_with_selenium(f'https://muckrack.com/{journalist_id}/interview')
                if int_html:
                    data['interviews'] = self.parse_interviews(BeautifulSoup(int_html, 'lxml'))
            
            # Ensure all fields exist
            data.setdefault('profile', {})
            data.setdefault('biography', '')
            data.setdefault('portfolio', [])
            data.setdefault('portfolio_count', len(data.get('portfolio', [])))
            data.setdefault('awards', [])
            data.setdefault('interviews', [])
            data['scraped_at'] = datetime.now().isoformat()
            
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            
            logger.info(f"✅ {name}: Done")
            return True
            
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            self._save_failed(name, url, str(e))
            return False
    
    def _save_failed(self, name: str, url: str, error: str):
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        failed_file = FAILED_DIR / f"{self.location}_failed.json"
        failed_data = json.loads(failed_file.read_text()) if failed_file.exists() else []
        failed_data.append({'name': name, 'url': url, 'error': error, 'timestamp': datetime.now().isoformat()})
        failed_file.write_text(json.dumps(failed_data, indent=2, ensure_ascii=False))
    
    def process_location(self, journalists: List[Dict]):
        logger.info(f"🚀 {self.location}: {len(journalists)} journalists")
        
        for i, j in enumerate(journalists, 1):
            logger.info(f"📦 {i}/{len(journalists)}")
            try:
                self.scrape_journalist(j)
            except Exception as e:
                logger.error(f"❌ Error: {e}")
            
            # Adaptive delay strategy - chess moves
            if i % 5 == 0:
                # Every 5 journalists, take a longer break
                delay = random.uniform(5, 10)
                logger.info(f"☕ Break time: {delay:.1f}s")
            elif i % 3 == 0:
                # Every 3 journalists, medium break
                delay = random.uniform(3, 6)
            else:
                # Normal random delay
                delay = random.uniform(1, 4)
            
            time.sleep(delay)
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        logger.info(f"🎉 {self.location} complete!")

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
        logger.info('\n⏹️ Stopped')
