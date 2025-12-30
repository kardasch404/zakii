#!/usr/bin/env python3
"""Final test with the exact HTML structure you provided"""

# Based on your HTML, let me create a test that shows what we should be getting
html_content = '''
<div class="profile-details-item">
    <strong>As seen in: </strong>
    <a href="/media-outlet/washpost">The Washington Post</a>,
    <a href="/media-outlet/bizinsider">Business Insider</a>,
    <a href="/media-outlet/dailymail">Daily Mail</a>,
    <a href="/media-outlet/estadao">Estadão</a>,
    <a href="/media-outlet/fox">Fox News</a>,
    <a href="/media-outlet/msn">MSN</a>,
    <a href="/media-outlet/msn-canada">MSN Canada</a>,
    <a href="/media-outlet/msn-za">MSN South Africa</a>,
    <a href="/media-outlet/msn-uk">MSN UK</a>,
    <a href="/media-outlet/independent">The Independent (UK)</a>,
    <a href="/media-outlet/time">TIME</a><span class="d-none">
        and <button class="js-as-seen-in-more btn btn-link p-0 align-baseline">more</button></span><span
        class="js-as-seen-in-hidden">, <a href="/media-outlet/usatoday">USA Today</a>, <a href="/media-outlet/yahoonews">Yahoo News</a>, <a href="/media-outlet/uknewsyahoo">Yahoo News UK</a>, <a href="/media-outlet/yahoo-sg">Yahoo Singapore</a>, <a href="/media-outlet/abcnews">ABC News</a>, <a href="/media-outlet/abcnewsone">ABC NewsOne</a>, <a href="/media-outlet/aol">Aol</a>, <a href="/media-outlet/buzzfeed">BuzzFeed</a>, <a href="/media-outlet/cbc">Canadian Broadcasting Corporation (CBC)</a>, <a href="/media-outlet/cnbc">CNBC</a>, <a href="/media-outlet/lanacion">La Nación (Argentina)</a>, <a href="/media-outlet/news">News.com.au</a>, <a href="/media-outlet/npr">NPR</a>, <a href="/media-outlet/pbs">PBS</a>, <a href="/media-outlet/PBS-newshour">PBS NewsHour</a>, <a href="/media-outlet/sfgate">SFGate</a>, <a href="/media-outlet/smh">Sydney Morning Herald</a>, <a href="/media-outlet/financeyahoo">Yahoo Finance</a>, <a href="/media-outlet/infinanceyahoo">Yahoo Finance India</a>, <a href="/media-outlet/ap-2">AP (The Associated Press)</a>, <a href="/media-outlet/ap">Associated Press</a>, <a href="/media-outlet/chicagotrib">Chicago Tribune</a>, <a href="/media-outlet/infobae">Infobae</a>, <a href="/media-outlet/stuff">Stuff.co.nz</a>, <a href="/media-outlet/substack">Substack</a>, <a href="/media-outlet/torontostar">The (Toronto) Star</a>, <a href="/media-outlet/dailybeast">The Daily Beast</a>, <a href="/media-outlet/theglobeandmail">The Globe and Mail</a>, <a href="/media-outlet/usn">U.S. News and World Report</a></span>
</div>
'''

from bs4 import BeautifulSoup

def test_html_parsing():
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Find all media outlet links
    all_links = soup.select('a[href*="/media-outlet/"]')
    print(f"📰 Total outlets in HTML: {len(all_links)}")
    
    # Find visible ones (not in hidden span)
    hidden_span = soup.select_one('span.js-as-seen-in-hidden')
    visible_links = []
    hidden_links = []
    
    if hidden_span:
        hidden_links = hidden_span.select('a[href*="/media-outlet/"]')
        print(f"📰 Hidden outlets: {len(hidden_links)}")
        
        # Get visible ones (all links minus hidden ones)
        for a in all_links:
            if a not in hidden_links:
                visible_links.append(a)
    else:
        visible_links = all_links
    
    print(f"📰 Visible outlets: {len(visible_links)}")
    print(f"📊 Total: {len(visible_links) + len(hidden_links)}")
    
    print("\n🔗 All outlets:")
    for i, a in enumerate(all_links, 1):
        print(f"   {i}. {a.get_text(strip=True)} -> {a.get('href')}")

if __name__ == "__main__":
    test_html_parsing()