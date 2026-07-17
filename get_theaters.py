import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        print("Navigating to theatres...")
        await page.goto("https://www.cineplex.com/en/theatres", wait_until="domcontentloaded", timeout=30000)
        
        await asyncio.sleep(5)
        
        content = await page.content()
        with open("cineplex_theatres.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("Saved to cineplex_theatres.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
