import requests
from bs4 import BeautifulSoup
from typing import List
import re
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import requests
from constant import HEADERS


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
        "X-Goog-FieldMask": "places.id,places.displayName,places.websiteUri,places.formattedAddress,places.reviewSummary,places.nationalPhoneNumber,nextPageToken",
    }

    payload = {
        "textQuery": query,
        "pageSize": 20,  # Adjust as needed; max is 20 for Places API
        "pageToken": None,  # For pagination; can be set to the nextPageToken from previous response
    }

    leads = []

    try:
        while True:
            response = requests.post(
                search_url, headers=headers, json=payload, timeout=10
            )
            if response.status_code != 200:
                print(f"API Error {response.status_code}: {response.text}")
                return []

            places = response.json().get("places", [])

            if not places:
                break

            for item in places:
                leads.append(
                    {
                        "place_id": item.get("id"),
                        # Extract text safely from the displayName localized object
                        "name": item.get("displayName", {}).get("text"),
                        # The website field is 'websiteUri' in Places API (New)
                        "website": item.get("websiteUri"),
                        "address": item.get("formattedAddress"),
                        "phone": item.get("nationalPhoneNumber"),
                    }
                )

            payload["pageToken"] = response.json().get("nextPageToken")
            if not payload["pageToken"]:
                break

        return leads
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []


def extract_meta_and_email(url: str):
    email = None
    meta_text = ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
                "meta", attrs={"property": "og:description"}
            )
            if meta_tag and meta_tag.get("content"):
                meta_text = meta_tag["content"]
            else:
                meta_text = " ".join([p.get_text() for p in soup.find_all("p")[:2]])

            emails = re.findall(
                r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resp.text
            )
            if emails:
                email = emails[0]
    except Exception:
        pass
    return email, meta_text[:300]


def find_instagram_on_website(website_url: str) -> str:
    """Scrapes the business homepage to locate an Instagram anchor link."""
    if not website_url or str(website_url).lower() == "nan":
        return None

    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    try:
        response = requests.get(website_url, headers=HEADERS, timeout=6)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "instagram.com" in href.lower():
                    return href
    except Exception:
        pass
    return None


def search_instagram_profile(
    display_name: str, address: str = "", phone: str = ""
) -> str:
    """Searches DuckDuckGo without an API key using name, address, and phone number."""
    # Extract locality/city keywords from formattedAddress (taking the first 2-3 parts)
    city_hint = ""
    if address and str(address).lower() != "nan":
        parts = [p.strip() for p in address.split(",") if p.strip()]
        city_hint = " ".join(parts[-3:]) if len(parts) >= 3 else address

    phone_clean = phone if (phone and str(phone).lower() != "nan") else ""

    # Build search query targeted to Instagram profiles
    query = f'{display_name} + {city_hint} + {phone_clean}'.strip()

    try:
        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    query,
                    region="in-en",
                    max_results=3,
                    safesearch="moderate",
                    backend="auto",
                )
            )
            for r in results:
                url = r.get("href") or r.get("link")
                return url
    except Exception:
        pass

    return None


def get_instagram_page(place_data: dict) -> str:
    """Main wrapper function that uses the full Google Places dictionary."""
    display_name = place_data.get("name", "")
    website = place_data.get("website", "")
    address = place_data.get("address", "")
    phone = place_data.get("phone", "")

    # 1. First priority: Check business website
    # if website:
    #     ig_from_site = find_instagram_on_website(website)
    #     if ig_from_site:
    #         return ig_from_site

    # 2. Fallback: Search the web directly
    if display_name:
        ig_from_search = search_instagram_profile(display_name, address, phone)
        if ig_from_search:
            return ig_from_search

    return None
