#!/usr/bin/env python3
"""Test scraper with sample journalists"""
import json
from pathlib import Path
from getjournalistdetails import JournalistScraper
import time

def test_journalist(location, name, url):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    scraper = JournalistScraper(location)
    data_file = Path(f'/home/kardasch/Desktop/muckrack/muckrack/datamuckrack/{location}/{name}/{name}.json')
    
    # Clear to force re-scrape
    if data_file.exists():
        data = json.loads(data_file.read_text())
        data['biography'] = ''
        data['profile'] = {}
        data_file.write_text(json.dumps(data, indent=2))
    
    # Scrape
    journalist = {'name': name, 'link': url}
    success = scraper.scrape_journalist(journalist)
    
    if success and data_file.exists():
        data = json.loads(data_file.read_text())
        print(f"\n✅ Name: {data['profile'].get('name')}")
        print(f"✅ Pronouns: {data['profile'].get('pronouns') or 'N/A'}")
        print(f"✅ Verified: {data['profile'].get('verified')}")
        print(f"✅ Location: {data['profile'].get('location') or 'N/A'}")
        print(f"✅ Jobs: {len(data['profile'].get('jobs', []))}")
        
        # Show beats with full URLs
        beats = data['profile'].get('beats', [])
        if beats:
            print(f"✅ Beats: {beats[0]}")
        
        # Show asSeenIn with full URLs
        seen = data['profile'].get('asSeenIn', [])
        if seen:
            print(f"✅ AsSeenIn: {seen[0]}")
        
        print(f"✅ Covers: {data['profile'].get('covers') or 'N/A'}")
        print(f"✅ Doesn't Cover: {data['profile'].get('doesnt_cover') or 'N/A'}")
        print(f"\n✅ Biography: {len(data.get('biography', ''))} chars")
        if data.get('biography'):
            print(f"Preview: {data['biography'][:200]}...")
    
    if scraper.driver:
        scraper.driver.quit()
    
    return success

if __name__ == '__main__':
    tests = [
        ('United States', 'Gentile, Carmen', 'https://muckrack.com/carmen-gentile'),
    ]
    
    for location, name, url in tests:
        test_journalist(location, name, url)
        time.sleep(5)  # Wait between tests
    
    print(f"\n{'='*60}")
    print("✅ Tests complete!")
