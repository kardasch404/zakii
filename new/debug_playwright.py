#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://muckrack.com/beats", wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        
        html = await page.content()
        
        with open('/home/kardasch/Desktop/muckrack/new/beats_page.html', 'w') as f:
            f.write(html)
        
        print(f"HTML length: {len(html)}")
        print(f"Saved to beats_page.html")
        
        # Check for locations
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        headings = soup.select('h3.mr-directory-group-heading')
        print(f"\nFound {len(headings)} headings:")
        for h in headings:
            print(f"  - {h.get_text(strip=True)}")
        
        await browser.close()

asyncio.run(main())
