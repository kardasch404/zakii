#!/usr/bin/env python3
"""Detailed test for Carmen with AJAX debugging"""
import json
from getjournalistdetails import JournalistScraper
from bs4 import BeautifulSoup

def test_carmen_detailed():
    scraper = JournalistScraper("test")
    
    try:
        scraper.init_driver()
        
        url = "https://muckrack.com/carmengentile"
        if scraper.try_navigate_with_retry(url):
            print(f"✅ Loaded: {url}\n")
            
            # Check for more button
            soup = BeautifulSoup(scraper.driver.page_source, 'lxml')
            container = soup.select_one('div.mr-card-content')
            
            if container:
                as_seen_item = None
                for item in container.select('div.profile-details-item'):
                    if item.select_one('strong') and 'As seen in:' in item.get_text():
                        as_seen_item = item
                        break
                
                if as_seen_item:
                    more_button = as_seen_item.select_one('button.js-as-seen-in-more')
                    print(f"📋 More button found: {more_button is not None}")
                    
                    visible = as_seen_item.select('a[href*="/media-outlet/"]')
                    print(f"📰 Visible outlets: {len(visible)}")
                    
                    if more_button:
                        print("\n🔄 Fetching AJAX endpoint...")
                        import requests
                        
                        ajax_url = "https://muckrack.com/carmengentile/as-seen-in.json"
                        cookies = {c['name']: c['value'] for c in scraper.driver.get_cookies()}
                        
                        response = requests.get(ajax_url, cookies=cookies, timeout=10)
                        print(f"Status: {response.status_code}")
                        
                        if response.status_code == 200:
                            data = response.json()
                            print(f"Response type: {type(data)}")
                            print(f"Items in response: {len(data) if isinstance(data, list) else 'N/A'}")
                            
                            if isinstance(data, list) and len(data) > 0:
                                print(f"\n📊 First 5 items from AJAX:")
                                for i, item in enumerate(data[:5], 1):
                                    print(f"   {i}. {item.get('title')} -> {item.get('view_url')}")
                                
                                print(f"\n📊 Total from AJAX: {len(data)}")
                                print(f"📊 Total with visible: {len(visible) + len(data)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper.driver:
            scraper.driver.quit()

if __name__ == "__main__":
    test_carmen_detailed()
