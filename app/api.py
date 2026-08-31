from fastapi import APIRouter, HTTPException, Depends
from .dependency import get_app_state
import pandas as pd
from .schemas import SearchRequest
from .utils import fetch_leads_places_api, extract_meta_and_email
from services import smtp, llm_agent

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

    api_key = app_state.settings.SEARCH_API_KEY
    search_url = app_state.settings.SEARCH_API_URL
    leads_raw = fetch_leads_places_api(
        payload.city, payload.query_type, search_url, api_key
    )
    if not leads_raw:
        raise HTTPException(
            status_code=404, detail="No leads found or Places API request failed."
        )

    processed_leads = []

    llm_client: llm_agent.LLMManager = app_state.get_llm_client_invoke
    smtp_client: smtp.EmailService = app_state.get_smtp_client_invoke

    for lead in leads_raw:
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
