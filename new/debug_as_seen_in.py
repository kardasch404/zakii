#!/usr/bin/env python3
"""Debug script to check HTML structure for 'As seen in' section"""
import time
from bs4 import BeautifulSoup
from getjournalistdetails import JournalistScraper

def debug_as_seen_in():
    """Debug the 'As seen in' section HTML"""
    
    scraper = JournalistScraper("debug")
    
    try:
        scraper.init_driver()
        
        # Load Susannah George profile
        url = "https://muckrack.com/susannah-george"
        if scraper.try_navigate_with_retry(url):
            print("✅ Page loaded successfully")
            
            # Get page source and parse
            soup = BeautifulSoup(scraper.driver.page_source, 'lxml')
            
            # Find the profile details item with "As seen in"
            details_item = soup.select_one('div.profile-details-item')
            if details_item and 'As seen in:' in details_item.get_text():
                print("\n📋 Found 'As seen in' section")
                
                # Check for visible outlets
                visible_outlets = details_item.select('a[href*="/media-outlet/"]')
                print(f"📰 Visible outlets: {len(visible_outlets)}")
                
                # Check for hidden span
                hidden_span = details_item.select_one('span.js-as-seen-in-hidden')
                if hidden_span:
                    print("🔍 Found js-as-seen-in-hidden span")
                    hidden_outlets = hidden_span.select('a[href*="/media-outlet/"]')
                    print(f"📰 Hidden outlets: {len(hidden_outlets)}")
                    
                    # Print first few hidden outlets
                    print("\n🔗 First 10 hidden outlets:")
                    for i, a in enumerate(hidden_outlets[:10]):
                        print(f"   {i+1}. {a.get_text(strip=True)} -> {a.get('href')}")
                    
                    if len(hidden_outlets) > 10:
                        print(f"   ... and {len(hidden_outlets) - 10} more")
                        
                else:
                    print("❌ No js-as-seen-in-hidden span found")
                
                # Check for "more" button
                more_button = details_item.select_one('button.js-as-seen-in-more')
                if more_button:
                    print("🔘 Found 'more' button")
                else:
                    print("❌ No 'more' button found")
                
                # Print the raw HTML structure
                print("\n📄 Raw HTML structure:")
                print("="*60)
                print(details_item.prettify()[:2000] + "..." if len(details_item.prettify()) > 2000 else details_item.prettify())
                print("="*60)
                
            else:
                print("❌ No 'As seen in' section found")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if scraper.driver:
            scraper.driver.quit()

if __name__ == "__main__":
    debug_as_seen_in()