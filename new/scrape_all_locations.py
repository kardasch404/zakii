#!/usr/bin/env python3
"""Scrape all journalists from all locations"""
import json
import time
import random
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / 'journalistv2' / 'locations'
CHECKPOINT_FILE = BASE_DIR / 'checkpoints' / 'checkpointsJournalistUrl.json'
LOCATION_HTML = Path(__file__).parent / 'location.html'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE.parent.mkdir(exist_ok=True)

def get_driver():
    """Create Selenium driver"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extract_locations():
    """Extract all location URLs from location.html"""
    html = LOCATION_HTML.read_text()
    soup = BeautifulSoup(html, 'lxml')
    
    locations = []
    for item in soup.select('div.mr-directory-group-item a'):
        href = item.get('href', '')
        name = item.get_text(strip=True)
        if href:
            url = f"https://muckrack.com{href}"
            locations.append({'name': name, 'url': url})
    
    return locations

def scrape_location(driver, location_url, location_name):
    """Scrape all journalists from a location with pagination"""
    journalists = []
    page = 1
    
    while True:
        url = f"{location_url}?page={page}" if page > 1 else location_url
        print(f"  📄 Page {page}: {url}")
        
        driver.get(url)
        time.sleep(random.uniform(1, 2))
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        
        # Extract journalists
        items = soup.select('div.mr-directory-item a')
        if not items:
            break
        
        for item in items:
            href = item.get('href', '')
            name = item.get_text(strip=True)
            if href:
                journalist_url = f"https://muckrack.com{href}"
                journalists.append({'name': name, 'url': journalist_url})
                print(f"    ✓ {name} - {journalist_url}")
        
        # Check for next page
        next_page = soup.select_one('ul.pager li:not(.disabled) a[href*="page="]')
        if not next_page:
            break
        
        page += 1
    
    return journalists

def load_checkpoint():
    """Load checkpoint"""
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {'completed': []}

def save_checkpoint(completed):
    """Save checkpoint"""
    CHECKPOINT_FILE.write_text(json.dumps({'completed': completed}, indent=2))

def main():
    """Main scraper"""
    locations = extract_locations()
    print(f"🌍 Found {len(locations)} locations\n")
    
    checkpoint = load_checkpoint()
    completed = set(checkpoint['completed'])
    
    driver = get_driver()
    
    try:
        for idx, loc in enumerate(locations, 1):
            name = loc['name']
            url = loc['url']
            
            if name in completed:
                print(f"[{idx}/{len(locations)}] ⏭️  Skipping {name} (already completed)\n")
                continue
            
            print(f"[{idx}/{len(locations)}] 🔍 Scraping {name}")
            print(f"  🔗 {url}")
            
            journalists = scrape_location(driver, url, name)
            
            # Save results
            output_file = OUTPUT_DIR / f"{name.lower().replace(' ', '_')}.json"
            data = {
                'location': name,
                'url': url,
                'total_journalists': len(journalists),
                'journalists': journalists
            }
            output_file.write_text(json.dumps(data, indent=2))
            
            print(f"  💾 Saved {len(journalists)} journalists to file://{output_file}")
            print(f"  ✅ Completed {name}\n")
            
            completed.add(name)
            save_checkpoint(list(completed))
            
            time.sleep(random.uniform(2, 4))
    
    finally:
        driver.quit()
    
    print(f"\n🎉 Completed all {len(locations)} locations!")

if __name__ == '__main__':
    main()
