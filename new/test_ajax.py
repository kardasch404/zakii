#!/usr/bin/env python3
"""Test AJAX endpoint directly"""
import requests
import json
from bs4 import BeautifulSoup

def test_ajax():
    # Test both journalists
    tests = [
        ("susannah-george", "Susannah George"),
        ("carmengentile", "Carmen Gentile")
    ]
    
    for journalist_id, name in tests:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        
        url = f"https://muckrack.com/{journalist_id}/as-seen-in.json"
        
        try:
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # Try to parse as JSON
                try:
                    data = response.json()
                    print(f"Response type: {type(data)}")
                    print(f"Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                    
                    # Parse HTML if present
                    if isinstance(data, dict) and 'html' in data:
                        soup = BeautifulSoup(data['html'], 'lxml')
                        outlets = soup.select('a[href*="/media-outlet/"]')
                        print(f"Outlets found: {len(outlets)}")
                        
                        if outlets:
                            print("\nFirst 10 outlets:")
                            for i, a in enumerate(outlets[:10], 1):
                                print(f"   {i}. {a.get_text(strip=True)}")
                    else:
                        # Try parsing as HTML directly
                        soup = BeautifulSoup(response.text, 'lxml')
                        outlets = soup.select('a[href*="/media-outlet/"]')
                        print(f"Outlets found in HTML: {len(outlets)}")
                        
                        if outlets:
                            print("\nFirst 10 outlets:")
                            for i, a in enumerate(outlets[:10], 1):
                                print(f"   {i}. {a.get_text(strip=True)}")
                        
                except Exception as e:
                    print(f"Error parsing: {e}")
                    print(f"Raw response (first 500 chars): {response.text[:500]}")
            else:
                print(f"Failed with status: {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_ajax()
