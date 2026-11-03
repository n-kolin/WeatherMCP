import re
from mcp.server.fastmcp import FastMCP
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright


mcp = FastMCP("weather-Israel")

# Module-level session globals — shared across tool calls in the same process
_playwright = None
_browser = None
_page = None

FORECAST_URL = "https://www.weather2day.co.il/forecast"

# CSS selectors for the forecast page UI.
# These are the recommended starting values from the design document.
# Verify against the live page with headless=False if they stop working.
SEARCH_SELECTOR = "input[placeholder]"
DROPDOWN_SELECTOR = "ul[role='listbox'], [class*='autocomplete'], [class*='suggestion']"
DROPDOWN_ITEM_SELECTOR = "ul[role='listbox'] li, [class*='suggestion-item'], [class*='autocomplete'] li"
CONTENT_SELECTOR = "main, [class*='forecast'], [class*='content']"


def _clean_content(text: str) -> str:
    """Collapse runs of whitespace, strip leading/trailing whitespace.

    Returns an empty string if the input is all whitespace.
    """
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned


@mcp.tool()
async def open_weather_forecast_israel() -> str:
    """Open the Israel weather forecast page in a Playwright browser session.

    Launches headless Chromium, navigates to the forecast URL, and stores
    the browser session in module-level globals for subsequent tool calls.
    """
    global _playwright, _browser, _page
    try:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        _page = await _browser.new_page()
        await _page.goto(FORECAST_URL, wait_until="domcontentloaded")
        return "Forecast page opened successfully"
    except PlaywrightTimeout:
        return "Error: Failed to open forecast page — page load timed out"
    except Exception as e:
        return f"Error: Failed to open forecast page — {e}"


@mcp.tool()
async def enter_weather_forecast_city_israel(city: str) -> str:
    """Type a city name into the search field on the forecast page.

    Args:
        city: The name of the Israeli city to search for.
    """
    if _page is None:
        return "Error: Browser session is not open. Call open_weather_forecast_israel first."
    try:
        await _page.fill(SEARCH_SELECTOR, city)
        await _page.wait_for_selector(DROPDOWN_SELECTOR, state="visible", timeout=5000)
        return f"City '{city}' entered successfully"
    except PlaywrightTimeout:
        return "Error: Search field not found within timeout"
    except Exception as e:
        return f"Error: Failed to enter city '{city}' — {e}"


@mcp.tool()
async def select_weather_forecast_city_israel() -> str:
    """Click the first city suggestion from the autocomplete dropdown.

    Waits for the page to finish loading after the selection.
    """
    if _page is None:
        return "Error: Browser session is not open. Call open_weather_forecast_israel first."
    try:
        await _page.locator(DROPDOWN_ITEM_SELECTOR).first.click()
        await _page.wait_for_load_state("domcontentloaded")
        return "City selected successfully"
    except PlaywrightTimeout:
        return "Error: Dropdown did not appear within timeout"
    except Exception as e:
        return f"Error: Failed to select city from dropdown — {e}"


@mcp.tool()
async def get_weather_forecast_content_israel() -> str:
    """Extract and return the cleaned weather forecast text from the current page.

    Reads the inner text of the forecast content area, collapses whitespace,
    and returns a single clean string suitable for an LLM.
    """
    if _page is None:
        return "Error: Browser session is not open. Call open_weather_forecast_israel first."
    try:
        raw = await _page.inner_text(CONTENT_SELECTOR)
        cleaned = _clean_content(raw)
        if not cleaned:
            return "Error: No forecast content found on page"
        return cleaned
    except PlaywrightTimeout:
        return "Error: Forecast content selector timed out"
    except Exception as e:
        return f"Error: Failed to retrieve forecast content — {e}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
