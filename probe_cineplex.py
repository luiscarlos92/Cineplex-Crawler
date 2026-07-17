import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        page = await browser.new_page()
        await page.goto('https://www.cineplex.com/', wait_until='domcontentloaded', timeout=45000)
        print('TITLE', await page.title())
        for label in ['Tickets', 'Showtimes', 'Theatres', 'Theater']:
            locator = page.locator(f'text={label}')
            if await locator.count() > 0:
                print('FOUND_TEXT', label)
                print(await locator.first.inner_text())
        for selector in ['a[href*="tickets"]', 'a[href*="showtime"]', 'button:has-text("Tickets")', 'button:has-text("Showtimes")']:
            loc = page.locator(selector)
            if await loc.count() > 0:
                print('FOUND_SELECTOR', selector)
                print(await loc.first.inner_text())
        await browser.close()

asyncio.run(main())
