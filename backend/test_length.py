import asyncio
import sys
from backend.agent.tools import BrowserManager
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

async def dump_links(url):
    bm = BrowserManager()
    await bm.initialize()
    print(f"\nNavigating to: {url}")
    success = await bm.navigate(url)
    if success:
        clean = await bm.get_clean_html()
        soup = BeautifulSoup(clean, 'html.parser')
        links = []
        for a in soup.find_all('a'):
            href = a.get('href')
            text = a.get_text(strip=True)
            if href:
                links.append((href, text))
        print(f"Found {len(links)} links on {url}:")
        for href, text in links:
            print(f"  {href} -> '{text}'")
    await bm.cleanup()

async def main():
    await dump_links("https://docs.crewai.com/")
    await dump_links("https://docs.crewai.com/en/introduction")

asyncio.run(main())
