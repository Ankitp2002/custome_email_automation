from fastapi import APIRouter, HTTPException, Depends
from .dependency import get_app_state
import os
import pandas as pd
from .schemas import SearchRequest
import requests
from bs4 import BeautifulSoup

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health Check Endpoint"""
    try:
        return {"message": "API is healthy and running."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-automation")
def run_automation(payload: SearchRequest, app_state=Depends(get_app_state)):
    leads_raw = fetch_leads_serpapi(payload.city, payload.query_type)
    if not leads_raw:
        raise HTTPException(
            status_code=404, detail="No leads found or SerpApi request failed."
        )

    processed_leads = []

    llm_client = app_state.get_llm_client_invoke
    smtp_client = app_state.get_smtp_client_invoke

    for lead in leads_raw[:5]:
        name = lead.get("name")
        site = lead.get("website")
        email, meta = extract_meta_and_email(site) if site else (None, "")

        email_body = ""
        status = "No Email Found"

        if email:
            try:
                email_body = llm_client(name, meta)
                smtp_client.send_email(
                    to_email=email, subject=f"Inquiry for {name}", body=email_body
                )
                status = "Sent"
            except Exception as e:
                status = f"Failed: {str(e)}"

        processed_leads.append(
            {
                "Name": name,
                "Website": site,
                "Email": email,
                "Metadata": meta,
                "Draft": email_body,
                "Status": status,
            }
        )

    pd.DataFrame(processed_leads).to_excel("leads_output.xlsx", index=False)

    return {
        "message": "Automation completed",
        "total_processed": len(processed_leads),
        "results": processed_leads,
    }


def fetch_leads_serpapi(city: str, query_type: str) -> List[dict]:
    api_key = os.getenv("SERPAPI_API_KEY")
    query = f"{query_type} in {city}"
    url = f"https://serpapi.com/search.json?engine=google&q={query}&api_key={api_key}"

    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return []

    results = response.json().get("organic_results", [])
    leads = []
    for item in results:
        leads.append({"name": item.get("title"), "website": item.get("link")})
    return leads


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
