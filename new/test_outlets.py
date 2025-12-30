#!/usr/bin/env python3
"""Quick test to verify As Seen In extraction works"""
from getjournalistdetails import JournalistScraper
import json

# Test with Christina Goldbaum (has "more" button)
scraper = JournalistScraper('test')
scraper.init_driver()

print("Testing Christina Goldbaum (has 'more' button)...")
result = scraper.scrape_journalist({
    'name': 'Test Christina',
    'link': 'https://muckrack.com/christina-goldbaum'
})

if result:
    from pathlib import Path
    file_path = Path('/home/kardasch/Desktop/muckrack/muckrack/datamuckrack/test/Test Christina/Test Christina.json')
    if file_path.exists():
        data = json.loads(file_path.read_text())
        print(f"\n✅ Journalist ID: {data.get('journalist_id')}")
        print(f"✅ URL: {data.get('url')}")
        print(f"✅ Extracted {len(data['profile']['asSeenIn'])} outlets")
        
        if len(data['profile']['asSeenIn']) > 50:
            print("🎉 SUCCESS! Got 50+ outlets (more button worked!)")
        elif len(data['profile']['asSeenIn']) > 11:
            print("✅ GOOD! Got more than 11 outlets")
        else:
            print("⚠️ Only got 11 outlets - more button may not have worked")
            print("\nFirst 11 outlets:")
            for outlet in data['profile']['asSeenIn'][:11]:
                print(f"  - {outlet['name']}")

# Test with Emmy Abdul Alim (no "more" button)
print("\n" + "="*60)
print("Testing Emmy Abdul Alim (no 'more' button)...")
result2 = scraper.scrape_journalist({
    'name': 'Test Emmy',
    'link': 'https://muckrack.com/emmy-abdul-alim-1'
})

if result2:
    file_path2 = Path('/home/kardasch/Desktop/muckrack/muckrack/datamuckrack/test/Test Emmy/Test Emmy.json')
    if file_path2.exists():
        data2 = json.loads(file_path2.read_text())
        print(f"\n✅ Journalist ID: {data2.get('journalist_id')}")
        print(f"✅ URL: {data2.get('url')}")
        print(f"✅ Extracted {len(data2['profile']['asSeenIn'])} outlets")
        print("\nOutlets:")
        for outlet in data2['profile']['asSeenIn']:
            print(f"  - {outlet['name']}")

scraper.driver.quit()
print("\n✅ Test complete!")
