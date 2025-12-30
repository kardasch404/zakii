#!/usr/bin/env python3
"""Test Susannah George AJAX endpoint"""
from getjournalistdetails import JournalistScraper
import time
import json

def test_susannah_ajax():
    scraper = JournalistScraper("test")
    
    try:
        scraper.init_driver()
        
        # Load main page first
        if scraper.try_navigate_with_retry("https://muckrack.com/susannah-george"):
            print("✅ Loaded main page\n")
            time.sleep(2)
            
            # Navigate to AJAX endpoint
            ajax_url = "https://muckrack.com/susannah-george/as-seen-in.json"
            print(f"🔄 Loading: {ajax_url}\n")
            
            scraper.driver.get(ajax_url)
            time.sleep(5)
            
            page_source = scraper.driver.page_source
            
            print(f"📄 Page length: {len(page_source)}")
            
            # Check if it's Cloudflare
            if 'cloudflare' in page_source.lower() or 'just a moment' in page_source.lower():
                print("❌ Cloudflare blocking detected")
            else:
                print("✅ No Cloudflare blocking\n")
                
                # Try to parse JSON
                try:
                    # Remove HTML tags
                    import re
                    json_text = re.sub(r'<[^>]+>', '', page_source).strip()
                    
                    data = json.loads(json_text)
                    print(f"✅ JSON parsed successfully!")
                    print(f"📊 Type: {type(data)}")
                    print(f"📊 Items: {len(data) if isinstance(data, list) else 'N/A'}")
                    
                    if isinstance(data, list) and len(data) > 0:
                        print(f"\n📰 First 5 outlets:")
                        for i, item in enumerate(data[:5], 1):
                            print(f"   {i}. {item.get('title')} -> {item.get('view_url')}")
                        
                        print(f"\n📊 Total outlets from AJAX: {len(data)}")
                        
                except Exception as e:
                    print(f"❌ JSON parse error: {e}")
                    print(f"\n📄 First 1000 chars of page:")
                    print(page_source[:1000])
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if scraper.driver:
            scraper.driver.quit()

if __name__ == "__main__":
    test_susannah_ajax()
