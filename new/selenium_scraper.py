#!/usr/bin/env python3
"""Simple Selenium-only scraper - Works when IP is not blocked"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set
import time
import random
import re
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

class JournalistScraper:
    def __init__(self, location_name: str):
        self.location = location_name
        self.driver = None
        self.checkpoint_file = CHECKPOINT_DIR / f'{location_name}_checkpoint.json'
        self.stats = {'total': 0, 'completed': 0, 'failed': 0, 'skipped': 0, 'start_time': None}
    
    def init_driver(self):
        if not self.driver:
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
            logger.info("🚗 Selenium ready")
    
    def fetch(self, url: str) -> str:
        try:
            self.init_driver()
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.mr-card-content, h1.profile-name"))
            )
            return self.driver.page_source
        except:
            return None
    
    def parse_profile(self, soup):
        intro = soup.select_one('div.profile-section.profile-intro')
        if not intro:
            return {}
        c = intro.select_one('div.mr-card-content')
        if not c:
            return {}
        
        pronouns = (p.get_text(strip=True) if (p := c.select_one('div.fs-6.text-muted.fw-light')) else '')
        intro_text = (desc.get_text(strip=True) if (desc := c.select_one('div.fs-5.fs-md-6.my-5')) else '')
        
        social_handles = []
        if intro_text:
            for handle in re.findall(r'@(\\w+)', intro_text):
                social_handles.append({'handle': f'@{handle}', 'link': f'https://twitter.com/{handle.lower()}'})
        
        jobs = []
        for li in c.select('ul.mr-person-job-items li'):
            text = li.get_text(strip=True).replace('\\uf1ad', '').strip()
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
            'socialHandles': social_handles,
            'covers': covers,
            'doesnt_cover': doesnt_cover,
            'intro': intro_text
        }
    
    def parse_bio(self, soup):
        bio_div = soup.select_one('div.profile-section.profile-bio div.mr-card-content')
        if not bio_div:
            return ''
        return '\\n\\n'.join([p.get_text(strip=True) for p in bio_div.select('p') if p.get_text(strip=True)])
    
    def parse_articles(self, soup):
        articles = []
        for item in soup.select('div.portfolio-item-container'):
            article = {}
            if h3 := item.select_one('h3.portfolio-item-title'):
                article['title'] = h3.get_text(strip=True)
            if link := item.select_one('a.portfolio-item-hover'):
                article['link'] = link.get('href', '')
            article['date'] = (date_span.get_text(strip=True) if (date_span := item.select_one('span.date')) else '')
            article['description'] = (p.get_text(strip=True) if (p := item.select_one('div.preview-contents p')) else '')
            article['image'] = (img.get('src', '') if (img := item.select_one('img')) else '')
            article['outlet'] = ''
            if pub_div := item.select_one('div.portfolio-item-publication a'):
                for cls in pub_div.get('class', []):
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
                award['year'] = parts[0].strip() if len(parts) == 2 else text
                award['award_name'] = parts[1].strip() if len(parts) == 2 else ''
            award['description'] = (p.get_text(strip=True) if (p := item.select_one('p.mt-4')) else '')
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
    
    def scrape_journalist(self, journalist: Dict) -> bool:
        name = journalist['name']
        url = journalist['link']
        journalist_id = url.split('/')[-1]
        
        missing = self.get_missing_sections(name)
        if not missing:
            self.stats['skipped'] += 1
            return True
        
        data_file = DATA_DIR / self.location / name / f'{name}.json'
        data = json.loads(data_file.read_text()) if data_file.exists() else {'name': name, 'link': url}
        data['url'] = url
        
        try:
            start_time = time.time()
            
            html = self.fetch(url)
            if not html:
                raise Exception("Failed to fetch")
            
            soup = BeautifulSoup(html, 'lxml')
            
            if 'profile' in missing:
                data['profile'] = self.parse_profile(soup)
            if 'bio' in missing:
                bio = self.parse_bio(soup)
                if not bio or len(bio) < 100:
                    time.sleep(random.uniform(0.5, 1))
                    bio_html = self.fetch(f'https://muckrack.com/{journalist_id}/bio')
                    if bio_html:
                        full_bio = self.parse_bio(BeautifulSoup(bio_html, 'lxml'))
                        if full_bio:
                            bio = full_bio
                data['biography'] = bio
            if 'portfolio' in missing:
                time.sleep(random.uniform(0.5, 1))
                port_html = self.fetch(f'https://muckrack.com/{journalist_id}/portfolio')
                if port_html:
                    data['portfolio'] = self.parse_articles(BeautifulSoup(port_html, 'lxml'))
                    data['portfolio_count'] = len(data['portfolio'])
            if 'awards' in missing:
                time.sleep(random.uniform(0.5, 1))
                award_html = self.fetch(f'https://muckrack.com/{journalist_id}/awards')
                if award_html:
                    data['awards'] = self.parse_awards(BeautifulSoup(award_html, 'lxml'))
            if 'interviews' in missing:
                time.sleep(random.uniform(0.5, 1))
                int_html = self.fetch(f'https://muckrack.com/{journalist_id}/interview')
                if int_html:
                    data['interviews'] = self.parse_interviews(BeautifulSoup(int_html, 'lxml'))
            
            data.setdefault('profile', {})
            data.setdefault('biography', '')
            data.setdefault('portfolio', [])
            data.setdefault('portfolio_count', len(data.get('portfolio', [])))
            data.setdefault('awards', [])
            data.setdefault('interviews', [])
            data['scraped_at'] = datetime.now().isoformat()
            
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            
            elapsed = time.time() - start_time
            logger.info(f"✅ {name}: {elapsed:.1f}s")
            self.stats['completed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            self.stats['failed'] += 1
            return False
    
    def load_checkpoint(self) -> Set[str]:
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text())
                completed = set(data.get('completed', []))
                logger.info(f"📋 Checkpoint: {len(completed)} done")
                return completed
            except:
                pass
        return set()
    
    def save_checkpoint(self, completed: Set[str]):
        elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        remaining = self.stats['total'] - len(completed)
        avg_time = elapsed / len(completed) if completed else 0
        eta = avg_time * remaining if remaining > 0 else 0
        
        data = {
            'location': self.location,
            'completed': list(completed),
            'last_updated': datetime.now().isoformat(),
            'stats': {
                **self.stats,
                'elapsed_seconds': int(elapsed),
                'elapsed_formatted': str(timedelta(seconds=int(elapsed))),
                'avg_time_per_journalist': f"{avg_time:.1f}s",
                'eta_seconds': int(eta),
                'eta_formatted': str(timedelta(seconds=int(eta))),
                'remaining': remaining
            }
        }
        self.checkpoint_file.write_text(json.dumps(data, indent=2))
    
    def log_progress(self, completed_count: int):
        elapsed = time.time() - self.stats['start_time']
        remaining = self.stats['total'] - completed_count
        avg_time = elapsed / completed_count if completed_count > 0 else 0
        eta = avg_time * remaining
        
        logger.info(f"📊 {completed_count}/{self.stats['total']} | "
                   f"✅ {self.stats['completed']} | ❌ {self.stats['failed']} | "
                   f"⏱️ {avg_time:.1f}s/each | ETA: {str(timedelta(seconds=int(eta)))}")
    
    def process_location(self, journalists: List[Dict]):
        completed = self.load_checkpoint()
        self.stats['total'] = len(journalists)
        self.stats['start_time'] = time.time()
        
        remaining = [j for j in journalists if j['name'] not in completed]
        
        logger.info(f"🚀 {self.location}: {len(journalists)} total, {len(remaining)} remaining")
        
        if not remaining:
            logger.info(f"✅ All done!")
            return
        
        for i, j in enumerate(remaining, 1):
            logger.info(f"📦 {i}/{len(remaining)} (Total: {len(completed) + i}/{len(journalists)}) - {j['name']}")
            
            try:
                success = self.scrape_journalist(j)
                if success:
                    completed.add(j['name'])
                    if i % 5 == 0:
                        self.save_checkpoint(completed)
                        self.log_progress(len(completed))
                
                # Close driver after each
                if self.driver:
                    try:
                        self.driver.quit()
                        self.driver = None
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                self.stats['failed'] += 1
            
            delay = random.uniform(1, 5)
            time.sleep(delay)
        
        self.save_checkpoint(completed)
        self.log_progress(len(completed))
        
        elapsed = time.time() - self.stats['start_time']
        logger.info(f"🎉 {self.location} done in {str(timedelta(seconds=int(elapsed)))}!")

def main():
    all_locations = [d for d in DATA_DIR.glob('*') if d.is_dir()]
    total_journalists = sum(len([d for d in loc.glob('*') if d.is_dir()]) for loc in all_locations)
    
    logger.info(f"🌍 Total: {total_journalists} journalists across {len(all_locations)} locations")
    
    for location_dir in all_locations:
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
        logger.info('\\n⏹️ Stopped')
