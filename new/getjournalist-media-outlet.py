#!/usr/bin/env python3
"""Fetch journalist media outlets from as-seen-in.json endpoint"""
import json
import time
import random
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "muckrack" / "datamuckrack"
OUTPUT_DIR = BASE_DIR / "testmedia"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_random_user_agent():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    ]
    return random.choice(agents)

def extract_journalist_id(url):
    """Extract journalist ID from profile URL"""
    # https://muckrack.com/joseph-goldstein -> joseph-goldstein
    return url.rstrip('/').split('/')[-1]

def init_driver():
    """Initialize Selenium driver - same as reference"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(f'--user-agent={get_random_user_agent()}')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def fetch_media_outlets(journalist_id, driver, profile_data=None):
    """Fetch media outlets from JSON endpoint if has more button, else from profile"""
    
    # Visit profile page first to establish session
    profile_url = f"https://muckrack.com/{journalist_id}"
    driver.get(profile_url)
    time.sleep(random.uniform(3, 5))
    
    page_source = driver.page_source
    has_more = 'js-as-seen-in-more' in page_source
    
    print(f"Has more button: {has_more}")
    
    if has_more:
        # Fetch from JSON endpoint using Selenium
        json_url = f"https://muckrack.com/{journalist_id}/as-seen-in.json"
        
        try:
            driver.get(json_url)
            time.sleep(random.uniform(3, 5))
            
            # Parse JSON from <pre> tags
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pre_tag = soup.find('pre')
            
            if pre_tag:
                data = json.loads(pre_tag.text)
                
                # Add full URL to view_url
                if data:
                    for outlet in data:
                        if 'view_url' in outlet and outlet['view_url']:
                            outlet['view_url'] = f"https://muckrack.com{outlet['view_url']}"
                
                return data if data else []
            else:
                print(f"⚠️ No <pre> tag found - Cloudflare blocked")
        except Exception as e:
            print(f"⚠️ JSON fetch failed: {e}")
        
        # Fallback to profile data
        print("→ Using profile data instead")
    
    # Use profile data
    if profile_data and 'profile' in profile_data and 'asSeenIn' in profile_data['profile']:
        as_seen_in = profile_data['profile']['asSeenIn']
        media_outlets = []
        for item in as_seen_in:
            outlet = {
                'title': item.get('name', ''),
                'view_url': item.get('link', ''),
                'from_profile': True
            }
            if has_more:
                outlet['note'] = 'Partial list - journalist has more outlets'
            media_outlets.append(outlet)
        return media_outlets
    return []

def process_all_journalists():
    """Process all journalists from datamuckrack directory"""
    
    journalist_files = list(DATA_DIR.rglob("*.json"))
    total = len(journalist_files)
    
    print(f"📊 Found {total} journalists to process\n")
    
    processed = 0
    failed = 0
    
    for idx, json_file in enumerate(journalist_files, 1):
        driver = None
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            url = data.get('url', '')
            name = data.get('name', 'Unknown')
            
            if not url:
                continue
            
            journalist_id = extract_journalist_id(url)
            
            print(f"[{idx}/{total}] 👤 {name}")
            print(f"🔗 {journalist_id}")
            
            driver = init_driver()
            
            # Fetch media outlets with profile data
            media_outlets = fetch_media_outlets(journalist_id, driver, data)
            
            if media_outlets is not None:
                output_file = OUTPUT_DIR / f"{journalist_id}.json"
                
                output_data = {
                    'journalist_id': journalist_id,
                    'name': name,
                    'url': url,
                    'media_outlets': media_outlets,
                    'fetched_at': datetime.now().isoformat()
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Saved {len(media_outlets)} outlets\n")
                processed += 1
            else:
                failed += 1
                print(f"⚠️ No data\n")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
            failed += 1
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    print(f"\n{'='*60}")
    print(f"🎉 COMPLETE!")
    print(f"✅ Processed: {processed}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Output: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}\n")

def test_single_journalist(journalist_id="joseph-goldstein"):
    """Test with a single journalist"""
    print(f"🧪 Testing: {journalist_id}\n")
    
    # Load profile data if exists
    profile_data = None
    for json_file in DATA_DIR.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('url', '').endswith(journalist_id):
                    profile_data = data
                    break
        except:
            pass
    
    driver = init_driver()
    
    try:
        media_outlets = fetch_media_outlets(journalist_id, driver, profile_data)
        
        if media_outlets is not None:
            print(f"✅ Found {len(media_outlets)} outlets\n")
            if len(media_outlets) > 0:
                print(json.dumps(media_outlets[:2], indent=2))
            
            test_file = OUTPUT_DIR / f"TEST_{journalist_id}.json"
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'journalist_id': journalist_id,
                    'media_outlets': media_outlets,
                    'fetched_at': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 {test_file}")
            return True
        else:
            print("❌ Failed")
            return False
    finally:
        driver.quit()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        test_id = sys.argv[2] if len(sys.argv) > 2 else "joseph-goldstein"
        test_single_journalist(test_id)
    else:
        # Process all
        process_all_journalists()
