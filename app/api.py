from fastapi import APIRouter, HTTPException, Depends
from .dependency import get_app_state
import pandas as pd
from .schemas import SearchRequest
from .utils import fetch_leads_places_api, get_human_driver
from services import smtp, llm_agent, social_media
import os
from constant import EMAIL_PROMPT

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

        try:
            selenium_driver = get_human_driver(headless=True)
            finder = social_media.SocialMediaService(lead, selenium_driver)
            results = finder.get_all()
        except Exception as e:
            print(f"Error occurred while processing lead: {e}")
            results = {}

        selenium_driver.quit()

        name = lead.get("name", "")
        status = "No Email Found"
        email = results.get("Email", "")
        llm_resp_email = {}

        if email:
            meta = {
                "reviewSummary": lead.get("reviewSummary", ""),
                "priceRange": lead.get("priceRange", ""),
                "rating": lead.get("rating", ""),
                "types": lead.get("types", []),
                "website": lead.get("website", ""),
                "name": lead.get("name", ""),
            }
            try:
                llm_resp_email = llm_client.invoke_llm(
                    llm_client.get_client("llm_gpt_oss_120"), meta, EMAIL_PROMPT
                )
                smtp_client.send_email(
                    to_email=email,
                    subject=llm_resp_email.get("subject", ""),
                    body=llm_resp_email.get("body", ""),
                )
                status = "Sent"
            except Exception as e:
                status = f"Failed: {str(e)}"

        processed_leads.append(
            {
                "Name": name,
                "Website": lead.get("website"),
                "email_subject": llm_resp_email.get("subject", ""),
                "email_draft": llm_resp_email.get("body", ""),
                "address": lead.get("address"),
                "meta": meta,
                **results,
                "Status": status,
                "user_validation": False,
            }
        )

    df = pd.DataFrame(processed_leads)

    if os.path.exists("leads_output.xlsx"):
        existing_df = pd.read_excel("leads_output.xlsx")

        # 1. Strip NaNs before checking membership
        existing_websites = set(existing_df["Website"].dropna().astype(str).str.strip())
        existing_emails = set(existing_df["Email"].dropna().astype(str).str.strip())
        existing_ig = set(existing_df["instagram"].dropna().astype(str).str.strip())
        existing_fb = set(existing_df["facebook"].dropna().astype(str).str.strip())
        existing_li = set(existing_df["linkedin"].dropna().astype(str).str.strip())

        # Pair Name + Address to avoid dropping common business names in different locations
        existing_name_addr = set(
            (
                existing_df["Name"].fillna("").astype(str).str.strip().str.lower()
                + "_"
                + existing_df["address"].fillna("").astype(str).str.strip().str.lower()
            )
        )

        # 2. Build masks only against non-null, valid values
        curr_name_addr = (
            df["Name"].fillna("").astype(str).str.strip().str.lower()
            + "_"
            + df["address"].fillna("").astype(str).str.strip().str.lower()
        )

        is_duplicate = (
            (
                df["Website"].notna()
                & df["Website"].astype(str).str.strip().isin(existing_websites)
            )
            | (
                df["Email"].notna()
                & df["Email"].astype(str).str.strip().isin(existing_emails)
            )
            | (
                df["instagram"].notna()
                & df["instagram"].astype(str).str.strip().isin(existing_ig)
            )
            | (
                df["facebook"].notna()
                & df["facebook"].astype(str).str.strip().isin(existing_fb)
            )
            | (
                df["linkedin"].notna()
                & df["linkedin"].astype(str).str.strip().isin(existing_li)
            )
            | (df["Name"].notna() & curr_name_addr.isin(existing_name_addr))
        )

        # Filter down to only non-duplicate rows
        df_new = df[~is_duplicate]

        # 3. Concatenate and save directly (NO os.remove needed)
        df = pd.concat([existing_df, df_new], ignore_index=True)

    df.to_excel("leads_output.xlsx", index=False)

    return {
        "message": "Automation completed",
        "total_processed": len(processed_leads),
        "results": processed_leads,
    }
