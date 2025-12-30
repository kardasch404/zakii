#!/usr/bin/env python3
"""Test script to extract just profile data from journalists"""
import json
from getjournalistdetails import JournalistScraper

def test_profile_extraction():
    """Test profile extraction for multiple journalists"""
    
    # Test URLs
    test_cases = [
        {
            "url": "https://muckrack.com/susannah-george",
            "journalist_id": "susannah-george",
            "name": "Susannah George"
        },
        {
            "url": "https://muckrack.com/ariana-abawe-1", 
            "journalist_id": "ariana-abawe-1",
            "name": "Ariana Abawe"
        }
    ]
    
    scraper = JournalistScraper("test")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            # Initialize browser for each test
            scraper.init_driver()
            
            # Navigate to profile
            if scraper.try_navigate_with_retry(test_case['url']):
                print(f"✅ Successfully loaded: {test_case['url']}")
                
                # Extract profile
                profile = scraper.extract_profile_details(test_case['journalist_id'])
                
                # Create result in desired format
                result = {
                    "url": test_case['url'],
                    "profile": profile
                }
                
                # Print key info
                print(f"\n📋 PROFILE SUMMARY:")
                print(f"   Name: {profile.get('name', 'N/A')}")
                print(f"   Verified: {profile.get('verified', False)}")
                print(f"   Location: {profile.get('location', 'N/A')}")
                print(f"   Jobs: {len(profile.get('jobs', []))}")
                print(f"   Beats: {len(profile.get('beats', []))}")
                print(f"   As seen in: {len(profile.get('asSeenIn', []))}")
                print(f"   Social handles: {len(profile.get('socialHandles', []))}")
                
                # Save to file
                filename = f'/home/kardasch/Desktop/muckrack/new/test_{test_case["journalist_id"]}.json'
                with open(filename, 'w') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"\n💾 Profile saved to: test_{test_case['journalist_id']}.json")
                
                # Show first few "As seen in" outlets
                if profile.get('asSeenIn'):
                    print(f"\n📰 First 5 'As seen in' outlets:")
                    for outlet in profile['asSeenIn'][:5]:
                        print(f"   - {outlet['name']}")
                    if len(profile['asSeenIn']) > 5:
                        print(f"   ... and {len(profile['asSeenIn']) - 5} more")
                
            else:
                print(f"❌ Failed to load: {test_case['url']}")
                
        except Exception as e:
            print(f"❌ Error testing {test_case['name']}: {e}")
        finally:
            if scraper.driver:
                try:
                    scraper.driver.quit()
                    scraper.driver = None
                except:
                    pass
    
    print(f"\n{'='*60}")
    print("🎉 TESTING COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_profile_extraction()