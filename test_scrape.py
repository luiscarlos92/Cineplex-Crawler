import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        print("Navigating to cineplex.com/en/movies...")
        await page.goto("https://www.cineplex.com/en/movies", wait_until="networkidle", timeout=30000)
        
        # Give it a bit of time
        await asyncio.sleep(5)
        
        # Try finding all h3 tags (often used for movie titles) or a tags
        print("Looking for movie elements...")
        
        # Find all images with alt text, sometimes posters have titles
        # Find all headings
        elements = await page.locator("h2, h3").all()
        titles = set()
        for el in elements:
            text = await el.text_content()
            if text and len(text.strip()) > 1 and text.strip() not in ["Filters", "Sort by", "Now Playing", "Coming Soon"]:
                titles.add(text.strip())
                
        print("Found Headings:", titles)

        # Also try looking for specific links
        links = await page.locator("a").all()
        for link in links:
            href = await link.get_attribute("href")
            if href and '/movie/' in href.lower():
                text = await link.text_content()
                if text and text.strip():
                    print("Found Movie Link text:", text.strip())

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
