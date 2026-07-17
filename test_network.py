import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        
        page.on("response", lambda response: print("API Response:", response.url) if 'api' in response.url.lower() or 'graphql' in response.url.lower() else None)
        
        print("Navigating...")
        await page.goto("https://www.cineplex.com/en/theatres", wait_until="networkidle", timeout=30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
