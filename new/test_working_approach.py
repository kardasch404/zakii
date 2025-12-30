#!/usr/bin/env python3
"""Test 20 journalists using working scraper approach"""
import json
from pathlib import Path
from datetime import datetime
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
TEST_DIR = BASE_DIR / 'test'
TEST_DIR.mkdir(exist_ok=True)

def get_random_user_agent():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    return random.choice(agents)

class TestScraper:
    def __init__(self):
        self.driver = None
    
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
    
    def try_navigate(self, url, max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    self.driver.delete_all_cookies()
                    time.sleep(2)
                
                self.driver.get(url)
                time.sleep(random.uniform(0.5, 1.0))
                
                html = self.driver.page_source
                if 'mr-card-content' in html:
                    return True
                
                if any(x in html.lower() for x in ['security check', 'captcha', 'blocked', 'just a moment']):
                    self.init_driver()
                    if attempt < max_retries:
                        time.sleep(2)
            except:
                if attempt == max_retries:
                    return False
                time.sleep(2)
        return False
    
    def extract_profile(self):
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        c = soup.select_one('div.mr-card-content')
        if not c:
            return {}
        
        profile = {}
        if img := c.select_one('img[src*="profile/images"]'):
            profile['avatar'] = img.get('src', '')
        if name := c.select_one('h1.profile-name'):
            profile['name'] = name.get_text(strip=True)
        profile['verified'] = bool(c.select_one('small.profile-verified'))
        
        jobs = []
        for item in c.select('ul.mr-person-job-items li.mr-person-job-item'):
            if outlet := item.select_one('a'):
                text = item.get_text(strip=True)
                jobs.append({'title': text.split(',')[0].strip(), 'outlet': outlet.get_text(strip=True)})
        profile['jobs'] = jobs
        return profile
    
    def extract_bio(self):
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        bio = soup.select_one('div.profile-section.profile-bio')
        if not bio:
            return ''
        return '\n\n'.join([p.get_text(strip=True) for p in bio.select('div.mr-card-content p') if p.get_text(strip=True)])
    
    def extract_portfolio(self):
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
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
    
    def extract_awards(self):
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        awards = []
        for item in soup.select('div.profile-award'):
            if h4 := item.select_one('h4.item-header'):
                awards.append({'title': h4.get_text(strip=True)})
        return awards
    
    def extract_interviews(self):
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        interviews = []
        for item in soup.select('div.profile-interview-answer'):
            if h4 := item.select_one('h4'):
                interviews.append({'question': h4.get_text(strip=True)})
        return interviews
    
    def scrape(self, journalist):
        name = journalist['name']
        url = journalist['link']
        jid = url.split('/')[-1]
        start = time.time()
        
        try:
            self.init_driver()
            
            if not self.try_navigate(url):
                raise Exception('Failed to load')
            
            data = {
                'url': url,
                'profile': self.extract_profile(),
                'biography': self.extract_bio(),
                'scraped_at': datetime.now().isoformat()
            }
            
            if self.try_navigate(f'https://muckrack.com/{jid}/portfolio'):
                time.sleep(1)
                data['portfolio'] = self.extract_portfolio()
            else:
                data['portfolio'] = []
            
            if self.try_navigate(f'https://muckrack.com/{jid}/awards'):
                time.sleep(1)
                data['awards'] = self.extract_awards()
            else:
                data['awards'] = []
            
            if self.try_navigate(f'https://muckrack.com/{jid}/interview'):
                time.sleep(1)
                data['interviews'] = self.extract_interviews()
            else:
                data['interviews'] = []
            
            return data, time.time() - start
        except Exception as e:
            return None, 0
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                except:
                    pass

def main():
    print("🎯 TEST SCRAPER - 20 Journalists")
    print("=" * 60)
    
    location_dir = DATA_DIR / 'Afghanistan'
    journalists = []
    for jdir in location_dir.glob('*'):
        if jdir.is_dir():
            jfile = jdir / f'{jdir.name}.json'
            if jfile.exists():
                try:
                    data = json.loads(jfile.read_text())
                    url = data.get('url') or data.get('link')
                    if url:
                        journalists.append({'name': jdir.name, 'link': url})
                except:
                    pass
    
    test = journalists[:20]
    print(f"📦 Testing: {len(test)} journalists\n")
    
    scraper = TestScraper()
    total_start = time.time()
    times = []
    success = 0
    
    for i, j in enumerate(test, 1):
        print(f"[{i}/20] {j['name']}")
        data, elapsed = scraper.scrape(j)
        times.append(elapsed)
        
        if data and data.get('profile'):
            name = j['name']
            path = TEST_DIR / name
            path.mkdir(exist_ok=True)
            (path / f'{name}.json').write_text(json.dumps(data, indent=2, ensure_ascii=False))
            success += 1
            print(f"  ✅ {elapsed:.1f}s")
        else:
            print(f"  ❌ Failed")
        
        if i % 5 == 0 and i < len(test):
            delay = random.uniform(1, 3)
            print(f"  🎮 {delay:.1f}s\n")
            time.sleep(delay)
        elif i < len(test):
            print(f"  ⏸️  {random.uniform(0.6, 1.0):.1f}s\n")
            time.sleep(random.uniform(0.6, 1.0))
    
    total = time.time() - total_start
    avg = sum(times) / len(times) if times else 0
    
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"Success: {success}/20 ({success/20*100:.1f}%)")
    print(f"Time: {total:.1f}s ({total/60:.1f} min)")
    print(f"Avg: {avg:.1f}s/journalist")
    print(f"Files: {len(list(TEST_DIR.glob('*/*.json')))}")
    
    if avg > 0 and success > 0:
        proj = avg * 113 + (113 // 5) * 2
        print(f"\n🎯 For 113 journalists:")
        print(f"  Time: {proj/60:.1f} min")
        print(f"  Speedup: {131/(proj/60):.1f}x! 🚀")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n⏹️ Stopped')
