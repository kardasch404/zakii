#!/usr/bin/env python3
"""Test Carmen Gentile profile"""
import json
from getjournalistdetails import JournalistScraper

def test_carmen():
    scraper = JournalistScraper("test")
    
    try:
        scraper.init_driver()
        
        url = "https://muckrack.com/carmengentile"
        journalist_id = "carmengentile"
        
        if scraper.try_navigate_with_retry(url):
            print(f"✅ Loaded: {url}")
            
            profile = scraper.extract_profile_details(journalist_id)
            
            result = {
                "url": url,
                "profile": profile
            }
            
            print(f"\n📋 PROFILE:")
            print(f"   Name: {profile.get('name')}")
            print(f"   Verified: {profile.get('verified')}")
            print(f"   Location: {profile.get('location')}")
            print(f"   Jobs: {len(profile.get('jobs', []))}")
            print(f"   Beats: {len(profile.get('beats', []))}")
            print(f"   As seen in: {len(profile.get('asSeenIn', []))}")
            
            with open('/home/kardasch/Desktop/muckrack/new/test_carmen.json', 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Saved to test_carmen.json")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if scraper.driver:
            scraper.driver.quit()

if __name__ == "__main__":
    test_carmen()
