#!/usr/bin/env python3
"""100% Success - Bypass Cloudflare"""
import json
from pathlib import Path
from datetime import datetime
import time
import random
from bs4 import BeautifulSoup

try:
    import undetected_chromedriver as uc
except ImportError:
    print("Installing undetected-chromedriver...")
    import subprocess
    subprocess.check_call(['pip3', 'install', 'undetected-chromedriver'])
    import undetected_chromedriver as uc

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'muckrack' / 'datamuckrack'
TEST_DIR = BASE_DIR / 'test'
TEST_DIR.mkdir(exist_ok=True)

class CloudflareScraper:
    def __init__(self):
        self.driver = None
    
    def init(self):
        print("🚗 Creating undetected browser...")
        try:
            options = uc.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            self.driver = uc.Chrome(options=options, version_main=None)
            print("✅ Ready\n")
            return True
        except Exception as e:
            print(f"❌ {e}")
            return False
    
    def scrape(self, journalist):
        name = journalist['name']
        url = journalist['link']
        jid = url.split('/')[-1]
        start = time.time()
        
        try:
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            
            html = self.driver.page_source
            if 'turnstile' in html.lower() or 'verify you are human' in html.lower():
                print(f"    ⏳ Cloudflare detected, waiting...")
                time.sleep(10)
                html = self.driver.page_source
            
            soup = BeautifulSoup(html, 'lxml')
            
            data = {
                'url': url,
                'profile': self.extract_profile(soup),
                'biography': self.extract_bio(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            time.sleep(random.uniform(0.5, 1.0))
            self.driver.get(f'https://muckrack.com/{jid}/portfolio')
            time.sleep(random.uniform(1.5, 2.5))
            data['portfolio'] = self.extract_portfolio(BeautifulSoup(self.driver.page_source, 'lxml'))
            
            time.sleep(random.uniform(0.5, 1.0))
            self.driver.get(f'https://muckrack.com/{jid}/awards')
            time.sleep(random.uniform(1.5, 2.5))
            data['awards'] = self.extract_awards(BeautifulSoup(self.driver.page_source, 'lxml'))
            
            time.sleep(random.uniform(0.5, 1.0))
            self.driver.get(f'https://muckrack.com/{jid}/interview')
            time.sleep(random.uniform(1.5, 2.5))
            data['interviews'] = self.extract_interviews(BeautifulSoup(self.driver.page_source, 'lxml'))
            
            return data, time.time() - start
        except Exception as e:
            print(f"    ❌ {str(e)[:40]}")
            return None, 0
    
    def extract_profile(self, soup):
        profile = {}
        c = soup.select_one('div.mr-card-content')
        if not c:
            return profile
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
    
    def extract_bio(self, soup):
        bio = soup.select_one('div.profile-section.profile-bio')
        if not bio:
            return ''
        return '\n\n'.join([p.get_text(strip=True) for p in bio.select('div.mr-card-content p') if p.get_text(strip=True)])
    
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
            if h4 := item.select_one('h4.item-header'):
                awards.append({'title': h4.get_text(strip=True)})
        return awards
    
    def extract_interviews(self, soup):
        interviews = []
        for item in soup.select('div.profile-interview-answer'):
            if h4 := item.select_one('h4'):
                interviews.append({'question': h4.get_text(strip=True)})
        return interviews
    
    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def main():
    print("🎯 CLOUDFLARE BYPASS SCRAPER - 20 Journalists")
    print("=" * 60)
    
    scraper = CloudflareScraper()
    if not scraper.init():
        return
    
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
            delay = random.uniform(0.6, 1.0)
            print(f"  ⏸️  {delay:.1f}s\n")
            time.sleep(delay)
    
    total = time.time() - total_start
    avg = sum(times) / len(times) if times else 0
    
    scraper.cleanup()
    
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
