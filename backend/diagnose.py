"""Diagnostic script to isolate the navigation failure."""
import asyncio
import urllib.request

async def main():
    # Step 1: Can we reach the URL at all via simple HTTP?
    print("=" * 60)
    print("STEP 1: Testing basic HTTP connectivity...")
    print("=" * 60)
    try:
        req = urllib.request.Request(
            "https://docs.crewai.com/",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"  HTTP Status: {resp.status}")
        data = resp.read()
        print(f"  Response size: {len(data)} bytes")
        print("  RESULT: Site is reachable via HTTP [PASS]")
    except Exception as e:
        print(f"  RESULT: Site is NOT reachable via HTTP [FAIL]")
        print(f"  Error: {e}")
        return

    # Step 2: Is Playwright installed correctly?
    print()
    print("=" * 60)
    print("STEP 2: Testing Playwright browser launch...")
    print("=" * 60)
    try:
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        print("  Browser launched successfully [PASS]")
    except Exception as e:
        print(f"  RESULT: Playwright browser FAILED to launch [FAIL]")
        print(f"  Error: {e}")
        print("  Fix: Run 'playwright install chromium'")
        return

    # Step 3: Can Playwright navigate to a simple page?
    print()
    print("=" * 60)
    print("STEP 3: Testing Playwright navigation to google.com...")
    print("=" * 60)
    try:
        await page.goto("https://www.google.com", timeout=15000)
        title = await page.title()
        print(f"  Page title: {title}")
        print("  RESULT: Playwright can navigate [PASS]")
    except Exception as e:
        print(f"  RESULT: Playwright CANNOT navigate [FAIL]")
        print(f"  Error: {e}")
        await browser.close()
        await pw.stop()
        return

    # Step 4: Can Playwright navigate to the target URL with 'commit'?
    print()
    print("=" * 60)
    print("STEP 4: Testing Playwright -> docs.crewai.com (wait_until=commit)...")
    print("=" * 60)
    try:
        resp = await page.goto("https://docs.crewai.com/", wait_until="commit", timeout=30000)
        print(f"  Response status: {resp.status if resp else 'No response object'}")
        content = await page.content()
        print(f"  Page content length: {len(content)} chars")
        title = await page.title()
        print(f"  Page title: {title}")
        print("  RESULT: Navigation with commit [PASS]")
    except Exception as e:
        print(f"  RESULT: Navigation with commit [FAIL]")
        print(f"  Error: {e}")
        try:
            content = await page.content()
            print(f"  Partial content length: {len(content)} chars")
        except:
            print("  No partial content available.")

    # Step 5: Try with 'domcontentloaded'
    print()
    print("=" * 60)
    print("STEP 5: Testing Playwright -> docs.crewai.com (wait_until=domcontentloaded)...")
    print("=" * 60)
    page2 = await browser.new_page()
    try:
        resp = await page2.goto("https://docs.crewai.com/", wait_until="domcontentloaded", timeout=30000)
        print(f"  Response status: {resp.status if resp else 'No response object'}")
        content = await page2.content()
        print(f"  Page content length: {len(content)} chars")
        title = await page2.title()
        print(f"  Page title: {title}")
        print("  RESULT: Navigation with domcontentloaded [PASS]")
    except Exception as e:
        print(f"  RESULT: Navigation with domcontentloaded [FAIL]")
        print(f"  Error: {e}")
        try:
            content = await page2.content()
            print(f"  Partial content length: {len(content)} chars")
        except:
            print("  No partial content available.")
    
    await page2.close()
    await browser.close()
    await pw.stop()
    print()
    print("=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)

asyncio.run(main())
