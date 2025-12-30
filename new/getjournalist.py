#!/usr/bin/env python3
"""Extract journalists using Playwright with cookies"""
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / 'journalistv2' / 'locations'
CHECKPOINT_FILE = BASE_DIR / 'checkpoints' / 'checkpointsJournalistUrl.json'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE.parent.mkdir(exist_ok=True)

# Add your cookies here from browser
COOKIES = [
    {'name': 'cf_clearance', 'value': 'arbzlyVd1X6LSi4rHL_VhBNjHwoyWQQCq3D8hEg5Clw-1766657158-1.2.1.1-JTW_lZOVQERhpCZZqShTD3yPSsuwFCZ8HmIP1ReLTUuVopKcgQXhesJOMz.bj6RZ9bfriD108qOKYDfFII5UPilZL7xNsitmxgXsgrYOd3op0gIyEasoQDkJzEn8phhCgUnjIOameeSG4ii9Om4xf4b.ojCwFHdZwqnH7XA9roEn2JCjw8r3aLsGKGYcJdWTaKEaYLZ86JU6pzzlUv9XZ1lFbV361Z.4eMYpckGqBqw0FvFc4LurhWYHZGAy2V23', 'domain': '.muckrack.com', 'path': '/'},
    {'name': 'csrftoken', 'value': 'mhigulv8htsmgvShL7abfpT8UaU7CWWY', 'domain': '.muckrack.com', 'path': '/'},
    {'name': 'sessionid', 'value': 'qrw6oflo1had20m6t2he9jji8uzvbumu', 'domain': '.muckrack.com', 'path': '/'},
]

LOCATIONS = {
    'afghanistan': 'https://muckrack.com/beat/afghanistan',
    'africa': 'https://muckrack.com/beat/africa',
    'australia': 'https://muckrack.com/beat/australia',
    'bangladesh': 'https://muckrack.com/beat/bangladesh',
    'belgium': 'https://muckrack.com/beat/belgium',
    'brazil': 'https://muckrack.com/beat/brazil',
    'canada': 'https://muckrack.com/beat/canada',
    'chile': 'https://muckrack.com/beat/chile',
    'china': 'https://muckrack.com/beat/china',
    'colombia': 'https://muckrack.com/beat/colombia',
    'egypt': 'https://muckrack.com/beat/egypt',
    'ethiopia': 'https://muckrack.com/beat/ethiopia',
    'france': 'https://muckrack.com/beat/france',
    'germany': 'https://muckrack.com/beat/germany',
    'india': 'https://muckrack.com/beat/india',
    'indonesia': 'https://muckrack.com/beat/indonesia',
    'ireland': 'https://muckrack.com/beat/ireland',
    'israel': 'https://muckrack.com/beat/israel',
    'italy': 'https://muckrack.com/beat/italy',
    'japan': 'https://muckrack.com/beat/japan',
    'kenya': 'https://muckrack.com/beat/kenya',
    'malawi': 'https://muckrack.com/beat/malawi',
    'mexico': 'https://muckrack.com/beat/mexico',
    'middleeast': 'https://muckrack.com/beat/middleeast',
    'newzealand': 'https://muckrack.com/beat/newzealand',
    'nigeria': 'https://muckrack.com/beat/nigeria',
    'pakistan': 'https://muckrack.com/beat/pakistan',
    'peru': 'https://muckrack.com/beat/peru',
    'philippines': 'https://muckrack.com/beat/philippines',
    'russia': 'https://muckrack.com/beat/russia',
    'rwanda': 'https://muckrack.com/beat/rwanda',
    'singapore': 'https://muckrack.com/beat/singapore',
    'southafrica': 'https://muckrack.com/beat/southafrica',
    'southeastasia': 'https://muckrack.com/beat/southeastasia',
    'spain': 'https://muckrack.com/beat/spain',
    'tanzania': 'https://muckrack.com/beat/tanzania',
    'turkey': 'https://muckrack.com/beat/turkey',
    'us': 'https://muckrack.com/beat/natlnews',
    'uganda': 'https://muckrack.com/beat/uganda',
    'uk': 'https://muckrack.com/beat/uk',
    'zambia': 'https://muckrack.com/beat/zambia',
}

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        return set(json.loads(CHECKPOINT_FILE.read_text())['completed'])
    return set()

def save_checkpoint(completed):
    CHECKPOINT_FILE.write_text(json.dumps({'completed': list(completed)}, indent=2))

async def scrape_location(page, location_name, url):
    print(f"🔍 {location_name}")
    journalists = []
    page_num = 1
    seen_urls = set()  # Track seen journalist URLs to detect duplicates
    
    while True:
        page_url = f"{url}?page={page_num}" if page_num > 1 else url
        await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(2000)
        
        items = await page.query_selector_all('div.mr-directory-item a')
        if not items:
            break
        
        page_journalists = []
        duplicates_found = False
        
        for item in items:
            href = await item.get_attribute('href')
            name = await item.inner_text()
            if href:
                full_url = f"https://muckrack.com{href}"
                
                # Check if we've seen this journalist before (duplicate page)
                if full_url in seen_urls:
                    duplicates_found = True
                    break
                
                seen_urls.add(full_url)
                page_journalists.append({'name': name.strip(), 'url': full_url})
        
        # If we found duplicates, we've reached the end
        if duplicates_found:
            print(f"  ⚠️  Page {page_num}: Duplicate content detected, stopping")
            break
        
        if not page_journalists:
            break
        
        journalists.extend(page_journalists)
        print(f"  ✓ Page {page_num}: {len(page_journalists)} journalists")
        
        # Check for next page button
        next_btn = await page.query_selector('ul.pager li:not(.disabled) a[href*="page="]')
        if not next_btn:
            break
        
        page_num += 1
    
    return journalists

async def main():
    completed = load_checkpoint()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        )
        
        # Add cookies
        await context.add_cookies(COOKIES)
        page = await context.new_page()
        
        for idx, (location_name, url) in enumerate(LOCATIONS.items(), 1):
            if location_name in completed:
                print(f"[{idx}/{len(LOCATIONS)}] ⏭️  {location_name}")
                continue
            
            print(f"[{idx}/{len(LOCATIONS)}] ", end='')
            journalists = await scrape_location(page, location_name, url)
            
            output_file = OUTPUT_DIR / f"{location_name}.json"
            data = {
                'location': location_name,
                'url': url,
                'total_journalists': len(journalists),
                'journalists': journalists
            }
            output_file.write_text(json.dumps(data, indent=2))
            
            print(f"  💾 {len(journalists)} journalists → file://{output_file}\n")
            
            completed.add(location_name)
            save_checkpoint(completed)
            
            await page.wait_for_timeout(2000)
        
        await browser.close()
    
    print('🎉 Done!')

if __name__ == '__main__':
    asyncio.run(main())
