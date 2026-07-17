import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Launch using local Microsoft Edge
        browser = await p.chromium.launch(channel="msedge", headless=False)
        page = await browser.new_page()
        
        print("Navigating to cineplex.com...")
        await page.goto("https://www.cineplex.com", wait_until="networkidle")
        
        print("Page loaded. Getting title...")
        title = await page.title()
        print(f"Title: {title}")
        
        # Save HTML for inspection
        content = await page.content()
        with open("cineplex_home.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("Saved HTML to cineplex_home.html. Closing browser in 5 seconds...")
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
