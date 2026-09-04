import requests
from typing import List
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def fetch_leads_places_api(
    city: str, query_type: str, search_url: str, api_key: str
) -> List[dict]:
    """Fetches chain petrol pump leads within a specific city using Google Places API (New)."""
    if not api_key:
        print("Error: GOOGLE_MAPS_API_KEY environment variable not set.")
        return []

    # Construct the query string (e.g., "Shell petrol pump in Ahmedabad")
    query = f"{query_type} in {city}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        # FieldMask limits the data returned to only what you need, minimizing costs
        "X-Goog-FieldMask": "places.id,places.priceRange,places.reviewSummary,places.types,places.googleMapsUri,places.displayName,places.websiteUri,places.formattedAddress,places.reviewSummary,places.nationalPhoneNumber,places.addressComponents,nextPageToken",
    }

    payload = {
        "textQuery": query,
        "pageSize": 20,  # Adjust as needed; max is 20 for Places API
        "pageToken": None,  # For pagination; can be set to the nextPageToken from previous response
    }

    leads = []

    count = 0
    try:
        while count < 5:  # Limit to 5 pages to avoid excessive API calls
            count += 1
            response = requests.post(
                search_url, headers=headers, json=payload, timeout=10
            )
            if response.status_code != 200:
                return leads

            places = response.json().get("places", [])

            if not places:
                break

            for item in places:
                country = [
                    i
                    for i in item.get("addressComponents", [])
                    if i.get("types", [""])[0] == "country"
                ]
                price = item.get("priceRange", {})
                leads.append(
                    {
                        "place_id": item.get("id"),
                        # Extract text safely from the displayName localized object
                        "name": item.get("displayName", {}).get("text"),
                        # The website field is 'websiteUri' in Places API (New)
                        "website": item.get("websiteUri"),
                        "address": item.get("formattedAddress"),
                        "phone": item.get("nationalPhoneNumber"),
                        "city": city,
                        "country": country[0].get("longText", "") if country else "",
                        "reviewSummary": item.get("reviewSummary", {})
                        .get("text", {})
                        .get("text", ""),
                        "priceRange": f"{price.get('startPrice', {}).get('unit', '')} - {price.get('endPrice', {}).get('unit', '')}",
                        "rating": item.get("rating", 0),
                        "googleMapsUri": item.get("googleMapsUri"),
                        "types": item.get("types", []),
                    }
                )

                payload["pageToken"] = response.json().get("nextPageToken")
                if not payload["pageToken"]:
                    break

        return leads
    except requests.exceptions.RequestException as e:
        return leads


def get_human_driver(
    headless: bool = False, profile_path: str = r"D:\selenium_chrome_profile"
):
    options = Options()

    # 1. Use a dedicated persistent profile (stores cookies, bypasses cold starts)
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")

    # 2. Window sizing and rendering flags
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    if headless:
        options.add_argument(
            "--headless"
        )  # Use new headless mode for better compatibility

    # 3. Suppress automation flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 4. Standard desktop user-agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    # 5. Overwrite navigator.webdriver on page init
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """},
    )

    return driver


def human_type(element, text: str, min_delay: float = 0.05, max_delay: float = 0.18):
    """Simulates realistic human typing with variable inter-key delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))


def search_by_custome_browser_human(driver, query: str) -> BeautifulSoup:
    # Step A: Navigate to Google's homepage first
    driver.get(
        f"https://duckduckgo.com/?ia=web&origin=funnel_home_google&t=h_&q={query}"
    )
    time.sleep(random.uniform(5, 10))  # Random delay to mimic human reading time
    return BeautifulSoup(driver.page_source, "html.parser")
