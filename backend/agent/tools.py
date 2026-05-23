import os
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import asyncio

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None

    async def initialize(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        self.page = await self.browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
            ignore_https_errors=True
        )
        
        # Bypass webdriver and headless detection
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)

    async def navigate(self, url: str) -> bool:
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            try:
                content = await self.page.content()
                if len(content) > 500 and "Just a moment" not in content and "cloudflare" not in content.lower():
                    print("Page timed out but content was partially loaded. Proceeding.")
                    return True
            except Exception:
                pass
            return False

    async def click(self, selector: str) -> bool:
        try:
            await self.page.click(selector, timeout=5000)
            # Wait for client-side routing and DOM updates (especially important for Single Page Apps)
            await asyncio.sleep(1.5)
            return True
        except Exception:
            return False

    async def type_text(self, selector: str, text: str) -> bool:
        try:
            await self.page.fill(selector, text, timeout=5000)
            return True
        except Exception:
            return False

    async def wait_for_selector(self, selector: str) -> bool:
        try:
            await self.page.wait_for_selector(selector, timeout=5000)
            return True
        except Exception:
            return False

    async def get_html(self) -> str:
        if self.page:
            return await self.page.content()
        return ""

    async def get_clean_html(self) -> str:
        if not self.page:
            return ""
        html = await self.page.content()
        soup = BeautifulSoup(html, 'html.parser')
        for element in soup(["script", "style", "svg", "meta", "path", "noscript"]):
            element.extract()
        return str(soup)

    async def get_text(self) -> str:
        if self.page:
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)
            return text
        return ""
        
    async def cleanup(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
