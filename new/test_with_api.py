#!/usr/bin/env python3
import json
import requests
from pathlib import Path
from datetime import datetime
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

TEST_DIR = Path(__file__).parent.parent / 'test'
TEST_DIR.mkdir(exist_ok=True)

def create_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def fetch_as_seen_in_json(journalist_id):
    try:
        url = f'https://muckrack.com/{journalist_id}/as-seen-in.json'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result = []
            for item in data:
                view_url = item.get('view_url', '')
                if view_url and not view_url.startswith('http'):
                    view_url = f"https://muckrack.com{view_url}"
                result.append({
                    'name': item.get('title', ''),
                    'link': view_url
                })
            return result
    except:
        pass
    return None

def extract_profile(driver, journalist_id):
    soup = BeautifulSoup(driver.page_source, 'lxml')
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
    
    # Check for "more" button
    has_more_button = bool(c.select_one('button.js-as-seen-in-more'))
    
    # Get asSeenIn
    if has_more_button:
        print(f"    🔍 Found 'more' button, fetching full list from API...")
        as_seen_full = fetch_as_seen_in_json(journalist_id)
        if as_seen_full:
            as_seen = as_seen_full
            print(f"    ✅ Fetched {len(as_seen)} outlets from API")
        else:
            as_seen = [{'name': a.get_text(strip=True), 'link': f"https://muckrack.com{a.get('href', '')}"} for a in c.select('div.profile-details-item a')]
    else:
        as_seen = [{'name': a.get_text(strip=True), 'link': f"https://muckrack.com{a.get('href', '')}"} for a in c.select('div.profile-details-item a')]
    
    return {
        'avatar': (img.get('src', '') if (img := c.select_one('img[src*="profile/images"]')) else ''),
        'name': (h1.get_text(strip=True) if (h1 := c.select_one('h1.profile-name')) else ''),
        'pronouns': pronouns,
        'verified': bool(c.select_one('small.profile-verified')),
        'jobs': jobs,
        'location': (s.get_text(strip=True) if (s := c.select_one('div.person-details-location span')) else ''),
        'beats': [{'name': a.get_text(strip=True), 'link': f"https://muckrack.com{a.get('href', '')}"} for a in c.select('div.person-details-beats a')],
        'asSeenIn': as_seen,
        'socialHandles': [{'handle': a.get_text(strip=True), 'link': a.get('href', '')} for a in c.select('a.tweet-url.username')],
        'covers': covers,
        'doesnt_cover': doesnt_cover,
        'intro': intro_text
    }

journalists = [
    {'name': 'Emma Graham-Harrison', 'url': 'https://muckrack.com/emma-graham-harrison'},
    {'name': 'Susannah George', 'url': 'https://muckrack.com/susannah-george'},
    {'name': 'Charlie Faulkner', 'url': 'https://muckrack.com/charlie-faulkner'}
]

for i, j in enumerate(journalists, 1):
    print(f"[{i}/3] {j['name']}")
    driver = create_driver()
    try:
        driver.get(j['url'])
        time.sleep(random.uniform(1, 2))
        
        journalist_id = j['url'].split('/')[-1]
        
        data = {
            'url': j['url'],
            'profile': extract_profile(driver, journalist_id),
            'scraped_at': datetime.now().isoformat()
        }
        
        path = TEST_DIR / j['name']
        path.mkdir(exist_ok=True)
        (path / f"{j['name']}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        
        print(f"  ✅ Saved ({len(data['profile'].get('asSeenIn', []))} outlets)")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    finally:
        driver.quit()
    
    if i < 3:
        time.sleep(random.uniform(1, 2))

print("\n✅ Done! Check test/ folder")
