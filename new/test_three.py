#!/usr/bin/env python3
"""Test script for 3 journalists"""
from getjournalistdetails import JournalistScraper
import json
from pathlib import Path

test_journalists = [
    {'name': 'Test Ariana', 'link': 'https://muckrack.com/ariana-abawe-1'},
    {'name': 'Test Julie', 'link': 'https://muckrack.com/juliemccarthyjm'},
    {'name': 'Test Zakarya', 'link': 'https://muckrack.com/zakarya-hassani-1'}
]

scraper = JournalistScraper('test')
scraper.init_driver()

for journalist in test_journalists:
    print(f"\n{'='*60}")
    print(f"Testing: {journalist['link']}")
    print('='*60)
    
    result = scraper.scrape_journalist(journalist)
    
    if result:
        file_path = Path(f'/home/kardasch/Desktop/muckrack/muckrack/datamuckrack/test/{journalist["name"]}/{journalist["name"]}.json')
        if file_path.exists():
            data = json.loads(file_path.read_text())
            
            print(f"\n✅ journalist_id: {data.get('journalist_id')}")
            print(f"✅ Profile name: {data['profile'].get('name')}")
            print(f"✅ Biography: {len(data.get('biography', ''))} chars")
            print(f"✅ Portfolio: {len(data.get('portfolio', []))} articles")
            print(f"✅ Awards: {len(data.get('awards', []))} awards")
            print(f"✅ Interviews: {len(data.get('interviews', []))} Q&As")
            
            if data.get('portfolio'):
                print(f"\n📰 First article: {data['portfolio'][0].get('title', 'N/A')}")
            if data.get('awards'):
                print(f"🏆 First award: {data['awards'][0].get('title', 'N/A')}")
            if data.get('interviews'):
                print(f"💬 First Q: {data['interviews'][0].get('question', 'N/A')[:50]}...")

scraper.driver.quit()
print("\n✅ Test complete!")
