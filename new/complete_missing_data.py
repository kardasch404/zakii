#!/usr/bin/env python3
"""Complete missing data scraper with as-seen-in.json"""
import json
import requests
from pathlib import Path
from datetime import datetime
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'

def get_user_agent():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    return random.choice(agents)

class CompleteScraper:
    def __init__(self):
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': get_user_agent()})
    
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
        options.add_argument(f'--user-agent={get_user_agent()}')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def fetch_as_seen_in_json(self, journalist_id):
        """Fetch as-seen-in.json from API"""
        try:
            url = f'https://muckrack.com/{journalist_id}/as-seen-in.json'
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Add base URL to view_url
                for item in data:
                    if item.get('view_url') and not item['view_url'].startswith('http'):
                        item['view_url'] = f"https://muckrack.com{item['view_url']}"
                return data
        except:
            pass
        return None
    
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
                href = outlet.get('href', '')
                jobs.append({
                    'title': text.split(',')[0].strip(),
                    'outlet': outlet.get_text(strip=True),
                    'outletLink': f"https://muckrack.com{href}" if href and not href.startswith('http') else href
                })
        profile['jobs'] = jobs
        
        if loc := c.select_one('div.person-details-location span'):
            profile['location'] = loc.get_text(strip=True)
        
        beats = []
        if beats_div := c.select_one('div.person-details-beats div'):
            for a in beats_div.select('a'):
                href = a.get('href', '')
                beats.append({
                    'name': a.get_text(strip=True),
                    'link': f"https://muckrack.com{href}" if href and not href.startswith('http') else href
                })
        profile['beats'] = beats
        
        as_seen = []
        for item in c.select('div.profile-details-item a'):
            href = item.get('href', '')
            as_seen.append({
                'name': item.get_text(strip=True),
                'link': f"https://muckrack.com{href}" if href and not href.startswith('http') else href
            })
        if hidden_span := c.select_one('span.js-as-seen-in-hidden'):
            for a in hidden_span.select('a'):
                href = a.get('href', '')
                as_seen.append({
                    'name': a.get_text(strip=True),
                    'link': f"https://muckrack.com{href}" if href and not href.startswith('http') else href
                })
        profile['asSeenIn'] = as_seen
        
        profile['covers'] = ''
        profile['doesntCover'] = ''
        for item in c.select('div.profile-details-item'):
            txt = item.get_text()
            if 'Covers:' in txt:
                profile['covers'] = txt.split('Covers:', 1)[1].strip()
            elif "Doesn't Cover:" in txt:
                profile['doesntCover'] = txt.split("Doesn't Cover:", 1)[1].strip()
        
        handles = []
        if social := c.select_one('div.fs-5.fs-md-6.my-5'):
            for a in social.select('a.tweet-url.username'):
                href = a.get('href', '')
                handles.append({
                    'handle': a.get_text(strip=True),
                    'link': f"https://muckrack.com{href}" if href and not href.startswith('http') else href
                })
        profile['socialHandles'] = handles
        
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
            if date := item.select_one('span.date'):
                article['date'] = date.get_text(strip=True)
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
    
    def complete_journalist_data(self, json_file):
        """Complete missing data for journalist"""
        try:
            existing = json.loads(json_file.read_text())
            url = existing.get('url')
            if not url:
                return False
            
            journalist_id = url.split('/')[-1]
            name = json_file.parent.name
            
            print(f"  📄 {name}")
            
            # Check what's missing
            needs_profile = not existing.get('profile') or not existing['profile'].get('name')
            needs_bio = not existing.get('biography')
            needs_portfolio = not existing.get('portfolio')
            needs_awards = not existing.get('awards')
            needs_interviews = not existing.get('interviews')
            needs_as_seen_full = True  # Always try to get full as-seen-in data
            
            if not any([needs_profile, needs_bio, needs_portfolio, needs_awards, needs_interviews, needs_as_seen_full]):
                print(f"    ✅ Complete")
                return True
            
            # Fetch as-seen-in.json first (no Selenium needed)
            if needs_as_seen_full:
                as_seen_data = self.fetch_as_seen_in_json(journalist_id)
                if as_seen_data:
                    existing['asSeenInFull'] = as_seen_data
                    print(f"    ✅ as-seen-in.json ({len(as_seen_data)} outlets)")
            
            # Only init driver if we need other data
            if any([needs_profile, needs_bio, needs_portfolio, needs_awards, needs_interviews]):
                self.init_driver()
                
                if needs_profile or needs_bio:
                    if self.try_navigate(url):
                        if needs_profile:
                            existing['profile'] = self.extract_profile()
                            print(f"    ✅ profile")
                        if needs_bio:
                            existing['biography'] = self.extract_bio()
                            print(f"    ✅ biography")
                
                if needs_portfolio:
                    if self.try_navigate(f'https://muckrack.com/{journalist_id}/portfolio'):
                        time.sleep(1)
                        existing['portfolio'] = self.extract_portfolio()
                        print(f"    ✅ portfolio")
                
                if needs_awards:
                    if self.try_navigate(f'https://muckrack.com/{journalist_id}/awards'):
                        time.sleep(1)
                        existing['awards'] = self.extract_awards()
                        print(f"    ✅ awards")
                
                if needs_interviews:
                    if self.try_navigate(f'https://muckrack.com/{journalist_id}/interview'):
                        time.sleep(1)
                        existing['interviews'] = self.extract_interviews()
                        print(f"    ✅ interviews")
                
                if self.driver:
                    self.driver.quit()
                    self.driver = None
            
            # Save updated data
            existing['updated_at'] = datetime.now().isoformat()
            json_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
            return True
            
        except Exception as e:
            print(f"    ❌ {str(e)[:50]}")
            return False

def main():
    print("🎯 COMPLETE MISSING DATA SCRAPER")
    print("=" * 60)
    
    scraper = CompleteScraper()
    
    # Process all locations
    for location_dir in sorted(DATA_DIR.glob('*')):
        if not location_dir.is_dir():
            continue
        
        print(f"\n📍 {location_dir.name}")
        
        journalists = list(location_dir.glob('*/*.json'))
        if not journalists:
            continue
        
        print(f"  Found: {len(journalists)} journalists")
        
        for i, json_file in enumerate(journalists[:20], 1):  # Test with 20
            scraper.complete_journalist_data(json_file)
            
            if i % 5 == 0:
                delay = random.uniform(1, 3)
                print(f"  🎮 {delay:.1f}s")
                time.sleep(delay)
            else:
                time.sleep(random.uniform(0.6, 1.0))
        
        break  # Test with one location first

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n⏹️ Stopped')
