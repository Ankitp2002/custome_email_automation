import requests
from bs4 import BeautifulSoup
from typing import List


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
        "X-Goog-FieldMask": "places.id,places.displayName,places.websiteUri,places.formattedAddress,places.nationalPhoneNumber",
    }

    payload = {
        "textQuery": query,
        "includedType": "gas_station",
    }

    try:
        response = requests.post(search_url, headers=headers, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"API Error {response.status_code}: {response.text}")
            return []

        places = response.json().get("places", [])
        leads = []

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
