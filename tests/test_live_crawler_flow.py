import asyncio
import os
import sys
from pathlib import Path

import pytest
from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import crawler  # noqa: E402


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "").casefold() not in {"1", "true", "yes"},
    reason="Set RUN_LIVE_TESTS=true to access the live Cineplex site.",
)
def test_live_tickets_drawer_exposes_structured_selectors():
    async def check_live_page():
        config = crawler.load_config()
        async with async_playwright() as playwright:
            launch_args = {"headless": True}
            if config.browser_channel:
                launch_args["channel"] = config.browser_channel
            browser = await playwright.chromium.launch(**launch_args)
            context_args = {"locale": config.locale, "timezone_id": config.timezone_id}
            if config.geolocation:
                context_args["geolocation"] = config.geolocation
                context_args["permissions"] = ["geolocation"]
            context = await browser.new_context(**context_args)
            page = await context.new_page()
            await page.goto(crawler.HOME_URL, wait_until="domcontentloaded", timeout=45_000)
            await crawler.open_tickets(page)

            assert await page.get_by_test_id("select-movie").is_visible()
            assert await page.get_by_test_id("select-date").is_visible()
            assert await page.get_by_test_id("select-theatre").is_visible()
            assert await page.get_by_test_id("select-filters").is_visible()
            await browser.close()

    asyncio.run(check_live_page())
