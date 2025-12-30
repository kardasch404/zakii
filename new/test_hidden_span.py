#!/usr/bin/env python3
"""Simple test to check the hidden span content"""
from bs4 import BeautifulSoup
from getjournalistdetails import JournalistScraper

def test_hidden_span():
    scraper = JournalistScraper("test")
    
    try:
        scraper.init_driver()
        
        if scraper.try_navigate_with_retry("https://muckrack.com/susannah-george"):
            soup = BeautifulSoup(scraper.driver.page_source, 'lxml')
            
            # Find the hidden span
            hidden_span = soup.select_one('span.js-as-seen-in-hidden')
            if hidden_span:
                print("✅ Found js-as-seen-in-hidden span")
                
                # Get all links in the hidden span
                hidden_links = hidden_span.select('a[href*="/media-outlet/"]')
                print(f"📰 Hidden outlets found: {len(hidden_links)}")
                
                # Print first 10
                for i, a in enumerate(hidden_links[:10]):
                    print(f"   {i+1}. {a.get_text(strip=True)} -> {a.get('href')}")
                
                if len(hidden_links) > 10:
                    print(f"   ... and {len(hidden_links) - 10} more")
                    
                # Also check visible ones
                details_item = soup.select_one('div.profile-details-item')
                if details_item and 'As seen in:' in details_item.get_text():
                    visible_links = []
                    for a in details_item.select('a[href*="/media-outlet/"]'):
                        # Skip if it's in the hidden span
                        if a not in hidden_links:
                            visible_links.append(a)
                    
                    print(f"📰 Visible outlets found: {len(visible_links)}")
                    print(f"📊 Total outlets: {len(visible_links) + len(hidden_links)}")
                    
            else:
                print("❌ No js-as-seen-in-hidden span found")
                
                # Check what we do have
                details_item = soup.select_one('div.profile-details-item')
                if details_item and 'As seen in:' in details_item.get_text():
                    all_links = details_item.select('a[href*="/media-outlet/"]')
                    print(f"📰 All outlets in section: {len(all_links)}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if scraper.driver:
            scraper.driver.quit()

if __name__ == "__main__":
    test_hidden_span()