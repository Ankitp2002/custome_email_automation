import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from selenium import webdriver
from duckduckgo_search import DDGS
import requests
from app.utils import search_by_custome_browser_human
from concurrent.futures import ThreadPoolExecutor, as_completed


class SocialMediaService:
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Routes to filter out so you only capture business/individual profile URLs
    EXCLUDED_PATHS = {
        "instagram page": {
            "p",
            "reel",
            "reels",
            "stories",
            "explore",
            "accounts",
            "developer",
            "about",
            "direct",
            "popular",
        },
        "facebook page": {
            "sharer",
            "share",
            "login",
            "pages",
            "groups",
            "events",
            "watch",
            "help",
            "policies",
            "privacy",
        },
        "linkedin profile": {
            "feed",
            "sharing",
            "login",
            "signup",
            "pulse",
            "learning",
            "help",
            "legal",
        },
        "email": [
            "info",
            "contact",
            "hello",
            "hi",
            "support",
            "help",
            "customercare",
            "customer.care",
            "customerservice",
            "service",
            "sales",
            "marketing",
            "admin",
            "administrator",
            "office",
            "enquiry",
            "enquiries",
            "inquiry",
            "reception",
            "billing",
            "accounts",
            "hr",
            "jobs",
            "careers",
            "noreply",
            "no-reply",
            "donotreply",
            "do-not-reply",
            "donotemail",
            "do-not-email",
        ],
    }

    PATTERNS = {
        "instagram page": re.compile(
            r"https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?",
            re.IGNORECASE,
        ),
        "facebook page": re.compile(
            r"https?://(?:www\.)?facebook\.com/([a-zA-Z0-9._-]+)/?",
            re.IGNORECASE,
        ),
        "linkedin profile": re.compile(
            r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)/?",
            re.IGNORECASE,
        ),
        "email": re.compile(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            re.IGNORECASE,
        ),
    }

    def __init__(self, place_data: dict, driver: webdriver.Chrome, timeout: int = 5):
        self.place_data = place_data
        self.timeout = timeout
        self.headers = {"User-Agent": self.USER_AGENT}
        self.driver = driver

    def _build_query(self, platform_keyword: str) -> str:
        parts = [
            platform_keyword,
            self.place_data.get("name", ""),
            self.place_data.get("city", ""),
            self.place_data.get("country", ""),
        ]
        return " ".join(p.strip() for p in parts if p and p.strip())

    def duckduck_go_search(self, query: str) -> list:
        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(
                        quote_plus(query),
                        region="in-en",
                        max_results=10,
                        safesearch="moderate",
                        backend="auto",
                    )
                )

                all_results = []
                for r in results:
                    url = r.get("href") or r.get("link")
                    all_results.append(url)

                return all_results

        except Exception:
            pass
        return []

    def bs4_search(self, query_url: str) -> list:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(
            query_url,
            headers=headers,
            timeout=5,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
        return [a.get("href") for a in soup.find_all("a", href=True) if a.get("href")][
            :50
        ]

    def selenium_search(self, query: str) -> list:
        soup = search_by_custome_browser_human(self.driver, query)
        return [a.get("href") for a in soup.find_all("a", href=True) if a.get("href")][
            :50
        ]

    def _fetch_query(self, query: str) -> list:
        return self.selenium_search(quote_plus(query))

    def _extract_google_redirect(self, raw_href: str) -> str:
        # Handles Google redirect format: /url?q=<target_url>&...
        if raw_href.startswith("/url?"):
            parsed = parse_qs(urlparse(raw_href).query)
            raw_href = parsed.get("q", [""])[0]
        return unquote(raw_href)

    def _find_social_link(self, platform: str) -> str:
        query = self._build_query(platform)
        list_of_urls = self._fetch_query(query)
        if not list_of_urls:
            return ""

        pattern = self.PATTERNS[platform]
        excluded = self.EXCLUDED_PATHS[platform]

        for url in list_of_urls:
            match = pattern.search(url)
            if match:
                identifier = match.group(1).lower()
                if identifier not in excluded:

                    # Return canonical matching URL without tracking query parameters
                    return match.group(0).split("?")[0].rstrip("/")

        return ""

    def get_instagram(self) -> str:
        return self._find_social_link("instagram page")

    def get_facebook(self) -> str:
        return self._find_social_link("facebook page")

    def get_linkedin(self) -> str:
        return self._find_social_link("linkedin profile")

    def get_email(self, url) -> str:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)

        emails = re.findall(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resp.text
        )
        excluded = self.EXCLUDED_PATHS["email"]
        for email in emails:
            email = email.lower().strip()
            username = email.split("@")[0]

            if username not in excluded:
                return email

        return ""

    def get_all(self) -> dict:
        social_info = {}

        social_info["instagram"] = self.get_instagram()
        social_info["facebook"] = self.get_facebook()
        social_info["linkedin"] = self.get_linkedin()

        for url in [
            self.place_data.get("website", ""),
            *social_info.values(),
        ]:
            if url:
                if email := self.get_email(url):
                    social_info["Email"] = email
                    break
        return social_info
