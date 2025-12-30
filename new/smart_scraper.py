#!/usr/bin/env python3
"""Smart scraper with human-like behavior - Evade Cloudflare"""
import json
import pickle
from pathlib import Path
from datetime import datetime
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
TEST_DIR = BASE_DIR / 'test'
SESSION_DIR = BASE_DIR / 'sessions'
SESSION_DIR.mkdir(exist_ok=True)
TEST_DIR.mkdir(exist_ok=True)

ACCOUNTS = [
    {'email': 'kardaschzakaria@gmail.com', 'password': 'KARDASCH-12zake', 'id': 'acc1'},
    {'email': 'zakariakardash@gmail.com', 'password': 'KARDASCH-12zake', 'id': 'acc2'}
]

class SmartSession:
    def __init__(self, account):
        self.account = account
        self.session_file = SESSION_DIR / f"{account['id']}_session.pkl"
        self.driver = None
    
    def create_driver(self):
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
        print(f"🔐 Logging in: {self.account['email']}")
        self.driver = self.create_driver()
        try:
            self.driver.get('https://muckrack.com/login')
            time.sleep(3)
            email_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'user_email')))
            email_input.send_keys(self.account['email'])
            password_input = self.driver.find_element(By.ID, 'user_password')
            password_input.send_keys(self.account['password'])
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
            submit_btn.click()
            time.sleep(5)
            cookies = self.driver.get_cookies()
            local_storage = self.driver.execute_script("return window.localStorage;")
            with open(self.session_file, 'wb') as f:
                pickle.dump({'cookies': cookies, 'local_storage': local_storage, 'timestamp': datetime.now().isoformat()}, f)
            print(f"✅ Logged in: {self.account['id']}")
            return True
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    def load_session(self):
        if not self.session_file.exists():
            return self.login()
        try:
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)
            self.driver = self.create_driver()
            self.driver.get('https://muckrack.com')
            for cookie in session_data['cookies']:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass
            if session_data.get('local_storage'):
                for key, value in session_data['local_storage'].items():
                    self.driver.execute_script(f"window.localStorage.setItem('{key}', '{value}');")
            self.driver.refresh()
            time.sleep(2)
            if 'login' not in self.driver.current_url:
                print(f"✅ Session loaded: {self.account['id']}")
                return True
            return self.login()
        except:
            return self.login()
    
    def get_page(self, url):
        try:
            self.driver.get(url)
            time.sleep(random.uniform(0.5, 1.2))
            return self.driver.page_source
        except:
            return None
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

class SmartScraper:
    def __init__(self):
        self.sessions = []
        self.current_idx = 0
    
    def init_sessions(self):
        print("🚀 Initializing sessions...")
        for account in ACCOUNTS:
            sm = SmartSession(account)
            if sm.load_session():
                self.sessions.append(sm)
        print(f"✅ {len(self.sessions)} sessions ready\n")
        return len(self.sessions) > 0
    
    def get_session(self):
        session = self.sessions[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.sessions)
        return session
    
    def scrape_journalist(self, journalist):
        name = journalist['name']
        url = journalist['link']
        journalist_id = url.split('/')[-1]
        session = self.get_session()
        start = time.time()
        
        try:
            html = session.get_page(url)
            if not html:
                raise Exception("Failed to load")
            
            soup = BeautifulSoup(html, 'lxml')
            data = {
                'url': url,
                'profile': self.extract_profile(soup),
                'biography': self.extract_bio(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            # Random delay between sections (human-like)
            time.sleep(random.uniform(0.4, 0.9))
            
            port_html = session.get_page(f'https://muckrack.com/{journalist_id}/portfolio')
            if port_html:
                data['portfolio'] = self.extract_portfolio(BeautifulSoup(port_html, 'lxml'))
            
            time.sleep(random.uniform(0.3, 0.7))
            
            award_html = session.get_page(f'https://muckrack.com/{journalist_id}/awards')
            if award_html:
                data['awards'] = self.extract_awards(BeautifulSoup(award_html, 'lxml'))
            
            time.sleep(random.uniform(0.3, 0.7))
            
            int_html = session.get_page(f'https://muckrack.com/{journalist_id}/interview')
            if int_html:
                data['interviews'] = self.extract_interviews(BeautifulSoup(int_html, 'lxml'))
            
            elapsed = time.time() - start
            print(f"  ✅ {name} ({elapsed:.1f}s)")
            return data
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            return None
    
    def extract_profile(self, soup):
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
                jobs.append({'title': title, 'outlet': outlet.get_text(strip=True)})
        profile['jobs'] = jobs
        if loc := container.select_one('div.person-details-location span'):
            profile['location'] = loc.get_text(strip=True)
        return profile
    
    def extract_bio(self, soup):
        bio_div = soup.select_one('div.profile-section.profile-bio')
        if not bio_div:
            return ''
        return '\n\n'.join([p.get_text(strip=True) for p in bio_div.select('div.mr-card-content p') if p.get_text(strip=True)])
    
    def extract_portfolio(self, soup):
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
    
    def extract_awards(self, soup):
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
    
    def extract_interviews(self, soup):
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
    
    def cleanup(self):
        for session in self.sessions:
            session.close()

def main():
    print("🎯 SMART SCRAPER - 20 Journalists Test")
    print("=" * 60)
    
    scraper = SmartScraper()
    if not scraper.init_sessions():
        print("❌ No sessions available")
        return
    
    # Load Afghanistan journalists
    location_dir = DATA_DIR / 'Afghanistan'
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
    
    test_journalists = journalists[:20]
    print(f"📦 Testing with {len(test_journalists)} journalists\n")
    
    total_start = time.time()
    times = []
    
    for i, journalist in enumerate(test_journalists, 1):
        print(f"[{i}/20] {journalist['name']}")
        
        j_start = time.time()
        data = scraper.scrape_journalist(journalist)
        j_elapsed = time.time() - j_start
        times.append(j_elapsed)
        
        if data:
            # Save to test folder
            name = journalist['name']
            dir_path = TEST_DIR / name
            dir_path.mkdir(exist_ok=True)
            file_path = dir_path / f'{name}.json'
            file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        
        # SMART DELAY: Random 1-3s between journalists
        if i < len(test_journalists):
            delay = random.uniform(1, 3)
            print(f"  ⏸️  Delay: {delay:.1f}s\n")
            time.sleep(delay)
    
    total_elapsed = time.time() - total_start
    avg_time = sum(times) / len(times)
    
    scraper.cleanup()
    
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"Total: {len(test_journalists)} journalists")
    print(f"Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"Avg: {avg_time:.1f}s per journalist")
    print(f"Success: {len(list(TEST_DIR.glob('*/*.json')))} files saved")
    print(f"\n📂 Results saved to: {TEST_DIR}")
    print(f"\n🎯 Projection for 113 journalists:")
    print(f"  Estimated: {(avg_time * 113 + 2.5 * 113)/60:.1f} minutes")
    print(f"  vs Current: 131 minutes")
    print(f"  Speedup: {131/((avg_time * 113 + 2.5 * 113)/60):.1f}x faster! 🚀")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n⏹️ Stopped')
