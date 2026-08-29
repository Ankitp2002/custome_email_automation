from pydantic import BaseModel


class SearchRequest(BaseModel):
    city: str
    query_type: str = "hotel"
