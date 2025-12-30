#!/usr/bin/env python3
"""Fully automated scraper - Auto login + 20 journalists test"""
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

class FullAutoScraper:
    def __init__(self, account):
        self.account = account
        self.session_file = SESSION_DIR / f"{account['id']}_session.pkl"
        self.driver = None
    
    def create_driver(self):
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def auto_login(self):
        print(f"🔐 Auto-login: {self.account['email']}")
        self.driver = self.create_driver()
        
        try:
            self.driver.get('https://muckrack.com/login')
            time.sleep(2)
            
            # Fill email
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'user_email'))
            )
            email_input.send_keys(self.account['email'])
            time.sleep(0.5)
            
            # Fill password
            password_input = self.driver.find_element(By.ID, 'user_password')
            password_input.send_keys(self.account['password'])
            time.sleep(0.5)
            
            # Click login
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
            submit_btn.click()
            
            print("  ⏳ Waiting...")
            time.sleep(5)
            
            # Check success
            if 'login' not in self.driver.current_url.lower():
                print(f"  ✅ Logged in!\n")
                
                # Save session
                cookies = self.driver.get_cookies()
                with open(self.session_file, 'wb') as f:
                    pickle.dump({'cookies': cookies, 'timestamp': datetime.now().isoformat()}, f)
                return True
            else:
                print(f"  ❌ Failed\n")
                return False
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}\n")
            return False
    
    def load_or_login(self):
        if self.session_file.exists():
            try:
                print(f"📂 Loading session: {self.account['id']}")
                with open(self.session_file, 'rb') as f:
                    session_data = pickle.load(f)
                
                self.driver = self.create_driver()
                self.driver.get('https://muckrack.com')
                time.sleep(1)
                
                for cookie in session_data['cookies']:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        pass
                
                self.driver.refresh()
                time.sleep(2)
                
                if 'login' not in self.driver.current_url.lower():
                    print(f"  ✅ Valid\n")
                    return True
                else:
                    self.driver.quit()
                    return self.auto_login()
            except:
                return self.auto_login()
        else:
            return self.auto_login()
    
    def get_page(self, url):
        try:
            self.driver.get(url)
            time.sleep(random.uniform(0.7, 1.3))
            return self.driver.page_source
        except:
            return None
    
    def scrape(self, journalist):
        name = journalist['name']
        url = journalist['link']
        journalist_id = url.split('/')[-1]
        start = time.time()
        
        try:
            html = self.get_page(url)
            if not html or len(html) < 1000:
                raise Exception("Empty")
            
            soup = BeautifulSoup(html, 'lxml')
            
            if 'cloudflare' in html.lower():
                print(f"    ⚠️ Cloudflare")
                return None
            
            data = {
                'url': url,
                'profile': self.extract_profile(soup),
                'biography': self.extract_bio(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            time.sleep(random.uniform(0.5, 0.9))
            port_html = self.get_page(f'https://muckrack.com/{journalist_id}/portfolio')
            data['portfolio'] = self.extract_portfolio(BeautifulSoup(port_html, 'lxml')) if port_html else []
            
            time.sleep(random.uniform(0.4, 0.8))
            award_html = self.get_page(f'https://muckrack.com/{journalist_id}/awards')
            data['awards'] = self.extract_awards(BeautifulSoup(award_html, 'lxml')) if award_html else []
            
            time.sleep(random.uniform(0.4, 0.8))
            int_html = self.get_page(f'https://muckrack.com/{journalist_id}/interview')
            data['interviews'] = self.extract_interviews(BeautifulSoup(int_html, 'lxml')) if int_html else []
            
            elapsed = time.time() - start
            print(f"  ✅ {elapsed:.1f}s")
            return data
        except Exception as e:
            print(f"  ❌ {str(e)[:30]}")
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
            if article.get('title'):
                articles.append(article)
        return articles
    
    def extract_awards(self, soup):
        awards = []
        for item in soup.select('div.profile-award'):
            award = {}
            if h4 := item.select_one('h4.item-header'):
                award['title'] = h4.get_text(strip=True)
            if award:
                awards.append(award)
        return awards
    
    def extract_interviews(self, soup):
        interviews = []
        for item in soup.select('div.profile-interview-answer'):
            interview = {}
            if h4 := item.select_one('h4'):
                interview['question'] = h4.get_text(strip=True)
            if interview:
                interviews.append(interview)
        return interviews
    
    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def main():
    print("🎯 FULL AUTO SCRAPER - 20 Journalists")
    print("=" * 60)
    
    scraper = FullAutoScraper(ACCOUNTS[0])
    if not scraper.load_or_login():
        print("❌ Login failed")
        return
    
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
    print(f"📦 Testing: {len(test_journalists)} journalists\n")
    
    total_start = time.time()
    times = []
    success = 0
    
    for i, journalist in enumerate(test_journalists, 1):
        print(f"[{i}/20] {journalist['name']}")
        
        j_start = time.time()
        data = scraper.scrape(journalist)
        j_elapsed = time.time() - j_start
        times.append(j_elapsed)
        
        if data and data.get('profile'):
            name = journalist['name']
            dir_path = TEST_DIR / name
            dir_path.mkdir(exist_ok=True)
            file_path = dir_path / f'{name}.json'
            file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            success += 1
        
        # Strategic delay every 5
        if i % 5 == 0 and i < len(test_journalists):
            delay = random.uniform(1, 3)
            print(f"  🎮 {delay:.1f}s\n")
            time.sleep(delay)
        elif i < len(test_journalists):
            delay = random.uniform(0.6, 1.0)
            print(f"  ⏸️  {delay:.1f}s\n")
            time.sleep(delay)
    
    total_elapsed = time.time() - total_start
    avg_time = sum(times) / len(times) if times else 0
    
    scraper.cleanup()
    
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"Total: {len(test_journalists)}")
    print(f"Success: {success}/{len(test_journalists)} ({success/len(test_journalists)*100:.1f}%)")
    print(f"Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"Avg: {avg_time:.1f}s/journalist")
    print(f"\n📂 {TEST_DIR}")
    print(f"Files: {len(list(TEST_DIR.glob('*/*.json')))}")
    
    if avg_time > 0 and success > 0:
        print(f"\n🎯 For 113 journalists:")
        total_time = avg_time * 113 + (113 // 5) * 2
        print(f"  Time: {total_time/60:.1f} min")
        print(f"  Speedup: {131/(total_time/60):.1f}x! 🚀")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n⏹️ Stopped')
