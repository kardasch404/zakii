#!/usr/bin/env python3
"""Multi-account parallel scraper - Target: 1-5s per journalist"""
import json
import logging
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
from queue import Queue

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
SESSION_DIR = BASE_DIR / 'sessions'
SESSION_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ACCOUNTS = [
    {'email': 'kardaschzakaria@gmail.com', 'password': 'KARDASCH-12zake', 'id': 'acc1'},
    {'email': 'zakariakardash@gmail.com', 'password': 'KARDASCH-12zake', 'id': 'acc2'}
]

class SessionManager:
    """Manage logged-in sessions with cookies"""
    
    def __init__(self, account: Dict):
        self.account = account
        self.session_file = SESSION_DIR / f"{account['id']}_session.pkl"
        self.driver = None
    
    def create_driver(self):
        """Create Chrome driver"""
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def login(self):
        """Login and save session"""
        logger.info(f"🔐 Logging in: {self.account['email']}")
        self.driver = self.create_driver()
        
        try:
            self.driver.get('https://muckrack.com/login')
            time.sleep(2)
            
            # Fill login form
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'user_email'))
            )
            email_input.send_keys(self.account['email'])
            
            password_input = self.driver.find_element(By.ID, 'user_password')
            password_input.send_keys(self.account['password'])
            
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
            submit_btn.click()
            
            time.sleep(5)
            
            # Save cookies
            cookies = self.driver.get_cookies()
            local_storage = self.driver.execute_script("return window.localStorage;")
            
            session_data = {
                'cookies': cookies,
                'local_storage': local_storage,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.session_file, 'wb') as f:
                pickle.dump(session_data, f)
            
            logger.info(f"✅ Logged in & saved: {self.account['id']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    def load_session(self):
        """Load saved session"""
        if not self.session_file.exists():
            return self.login()
        
        try:
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            self.driver = self.create_driver()
            self.driver.get('https://muckrack.com')
            
            # Restore cookies
            for cookie in session_data['cookies']:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass
            
            # Restore localStorage
            if session_data.get('local_storage'):
                for key, value in session_data['local_storage'].items():
                    self.driver.execute_script(f"window.localStorage.setItem('{key}', '{value}');")
            
            self.driver.refresh()
            time.sleep(2)
            
            # Verify login
            if 'login' not in self.driver.current_url:
                logger.info(f"✅ Session loaded: {self.account['id']}")
                return True
            else:
                logger.warning(f"⚠️ Session expired: {self.account['id']}")
                return self.login()
                
        except Exception as e:
            logger.error(f"❌ Session load failed: {e}")
            return self.login()
    
    def get_page(self, url: str) -> str:
        """Fetch page with session"""
        try:
            self.driver.get(url)
            time.sleep(random.uniform(0.3, 0.8))
            return self.driver.page_source
        except Exception as e:
            logger.error(f"❌ Fetch error: {e}")
            return None
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

class FastScraper:
    """Fast parallel scraper using multiple accounts"""
    
    def __init__(self):
        self.sessions = []
        self.current_session_idx = 0
        self.lock = threading.Lock()
    
    def init_sessions(self):
        """Initialize all account sessions"""
        logger.info("🚀 Initializing sessions...")
        for account in ACCOUNTS:
            sm = SessionManager(account)
            if sm.load_session():
                self.sessions.append(sm)
        
        logger.info(f"✅ {len(self.sessions)} sessions ready")
        return len(self.sessions) > 0
    
    def get_session(self) -> SessionManager:
        """Round-robin session selection"""
        with self.lock:
            session = self.sessions[self.current_session_idx]
            self.current_session_idx = (self.current_session_idx + 1) % len(self.sessions)
            return session
    
    def scrape_journalist_fast(self, journalist: Dict) -> Dict:
        """Scrape journalist with minimal delays"""
        name = journalist['name']
        url = journalist['link']
        journalist_id = url.split('/')[-1]
        
        session = self.get_session()
        start = time.time()
        
        try:
            # Main profile
            html = session.get_page(url)
            if not html:
                raise Exception("Failed to load page")
            
            soup = BeautifulSoup(html, 'lxml')
            
            data = {
                'url': url,
                'profile': self.extract_profile(soup),
                'biography': self.extract_bio(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            # Portfolio (parallel fetch)
            port_html = session.get_page(f'https://muckrack.com/{journalist_id}/portfolio')
            if port_html:
                data['portfolio'] = self.extract_portfolio(BeautifulSoup(port_html, 'lxml'))
            
            # Awards
            award_html = session.get_page(f'https://muckrack.com/{journalist_id}/awards')
            if award_html:
                data['awards'] = self.extract_awards(BeautifulSoup(award_html, 'lxml'))
            
            # Interviews
            int_html = session.get_page(f'https://muckrack.com/{journalist_id}/interview')
            if int_html:
                data['interviews'] = self.extract_interviews(BeautifulSoup(int_html, 'lxml'))
            
            elapsed = time.time() - start
            logger.info(f"✅ {name} ({elapsed:.1f}s)")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            return None
    
    def extract_profile(self, soup) -> dict:
        """Extract profile details"""
        profile = {}
        container = soup.select_one('div.mr-card-content')
        if not container:
            return profile
        
        if img := container.select_one('img[src*="profile/images"]'):
            profile['avatar'] = img.get('src', '')
        
        if name := container.select_one('h1.profile-name'):
            profile['name'] = name.get_text(strip=True)
        
        profile['verified'] = bool(container.select_one('small.profile-verified'))
        
        jobs = []
        for item in container.select('ul.mr-person-job-items li.mr-person-job-item'):
            if outlet := item.select_one('a'):
                text = item.get_text(strip=True)
                title = text.split(',')[0].strip()
                jobs.append({
                    'title': title,
                    'outlet': outlet.get_text(strip=True),
                    'outletLink': outlet.get('href', '')
                })
        profile['jobs'] = jobs
        
        if loc := container.select_one('div.person-details-location span'):
            profile['location'] = loc.get_text(strip=True)
        
        return profile
    
    def extract_bio(self, soup) -> str:
        """Extract biography"""
        bio_div = soup.select_one('div.profile-section.profile-bio')
        if not bio_div:
            return ''
        return '\n\n'.join([p.get_text(strip=True) for p in bio_div.select('div.mr-card-content p') if p.get_text(strip=True)])
    
    def extract_portfolio(self, soup) -> list:
        """Extract portfolio"""
        articles = []
        for item in soup.select('div.portfolio-item-container'):
            article = {}
            if h3 := item.select_one('h3.portfolio-item-title'):
                article['title'] = h3.get_text(strip=True)
            if link := item.select_one('a.portfolio-item-hover'):
                article['link'] = link.get('href', '')
            if date := item.select_one('span.date'):
                article['date'] = date.get_text(strip=True)
            if article.get('title'):
                articles.append(article)
        return articles
    
    def extract_awards(self, soup) -> list:
        """Extract awards"""
        awards = []
        for item in soup.select('div.profile-award'):
            award = {}
            if h4 := item.select_one('h4.item-header'):
                award['title'] = h4.get_text(strip=True)
            if h5 := item.select_one('h5'):
                text = h5.get_text(strip=True)
                parts = text.split('-', 1)
                award['year'] = parts[0].strip() if len(parts) >= 1 else ''
            if award:
                awards.append(award)
        return awards
    
    def extract_interviews(self, soup) -> list:
        """Extract interviews"""
        interviews = []
        for item in soup.select('div.profile-interview-answer'):
            interview = {}
            if h4 := item.select_one('h4'):
                interview['question'] = h4.get_text(strip=True)
            if answer := item.select_one('div.interview-answer'):
                interview['answer'] = answer.get_text(strip=True)
            if interview:
                interviews.append(interview)
        return interviews
    
    def process_batch(self, journalists: List[Dict], location: str):
        """Process journalists in parallel"""
        logger.info(f"📦 Processing {len(journalists)} journalists from {location}")
        
        for i, journalist in enumerate(journalists, 1):
            data = self.scrape_journalist_fast(journalist)
            
            if data:
                # Save
                name = journalist['name']
                dir_path = DATA_DIR / location / name
                dir_path.mkdir(parents=True, exist_ok=True)
                
                file_path = dir_path / f'{name}.json'
                file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Minimal delay
            if i < len(journalists):
                time.sleep(random.uniform(1, 2))
        
        logger.info(f"✅ Batch complete: {location}")
    
    def cleanup(self):
        """Close all sessions"""
        for session in self.sessions:
            session.close()

def main():
    scraper = FastScraper()
    
    if not scraper.init_sessions():
        logger.error("❌ No sessions available")
        return
    
    # Example: Process one location
    location = 'Afghanistan'
    location_dir = DATA_DIR / location
    
    if not location_dir.exists():
        logger.error(f"❌ Location not found: {location}")
        return
    
    journalists = []
    for journalist_dir in location_dir.glob('*'):
        if journalist_dir.is_dir():
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
        start = time.time()
        scraper.process_batch(journalists[:10], location)  # Test with 10
        elapsed = time.time() - start
        logger.info(f"⏱️ Total: {elapsed:.1f}s | Avg: {elapsed/min(10, len(journalists)):.1f}s/journalist")
    
    scraper.cleanup()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('\n⏹️ Stopped')
