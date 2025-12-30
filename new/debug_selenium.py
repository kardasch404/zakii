#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)
driver.get("https://muckrack.com/beat/afghanistan")
time.sleep(5)

soup = BeautifulSoup(driver.page_source, 'lxml')

# Save HTML
with open('/home/kardasch/Desktop/muckrack/new/debug_page.html', 'w') as f:
    f.write(driver.page_source)

# Check for journalists
items = soup.select('div.mr-directory-item a')
print(f"Found {len(items)} journalist items")

for i, item in enumerate(items[:5]):
    print(f"{i+1}. {item.get_text(strip=True)} -> {item.get('href')}")

driver.quit()
print("\nHTML saved to debug_page.html")
