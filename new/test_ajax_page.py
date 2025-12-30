#!/usr/bin/env python3
"""Check what browser sees at AJAX URL"""
from getjournalistdetails import JournalistScraper
import time

def test_ajax_page():
    scraper = JournalistScraper("test")
    
    try:
        scraper.init_driver()
        
        # First load main page
        if scraper.try_navigate_with_retry("https://muckrack.com/carmengentile"):
            print("✅ Loaded main page\n")
            
            # Now navigate to AJAX URL
            ajax_url = "https://muckrack.com/carmengentile/as-seen-in.json"
            print(f"🔄 Navigating to: {ajax_url}")
            
            scraper.driver.get(ajax_url)
            time.sleep(3)
            
            page_source = scraper.driver.page_source
            print(f"\n📄 Page source length: {len(page_source)}")
            print(f"📄 First 500 chars:\n{page_source[:500]}")
            print(f"\n📄 Last 200 chars:\n{page_source[-200:]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if scraper.driver:
            scraper.driver.quit()

if __name__ == "__main__":
    test_ajax_page()
