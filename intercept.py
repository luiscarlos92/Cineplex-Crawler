import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=False)
        page = await browser.new_page()
        
        # Intercept and print all API requests
        def handle_response(response):
            if "api" in response.url or "graphql" in response.url or "movies" in response.url or "theatres" in response.url:
                if response.request.resource_type in ["fetch", "xhr"]:
                    print(f"[{response.status}] {response.url}")
        
        page.on("response", handle_response)
        
        print("Navigating to cineplex.com...")
        await page.goto("https://www.cineplex.com/en", wait_until="networkidle")
        
        print("Waiting 10 seconds for any dynamic requests...")
        await asyncio.sleep(10)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
