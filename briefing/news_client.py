"""Web news search for a company using Google Custom Search or SerpAPI."""
import os
import requests


def get_company_news(company_name: str, max_results: int = 5) -> list[dict]:
    """
    Fetch recent news about a company.
    Uses Google Custom Search JSON API if GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID are set,
    otherwise falls back to SerpAPI (SERPAPI_KEY).
    """
    if os.getenv("GOOGLE_CSE_API_KEY") and os.getenv("GOOGLE_CSE_ID"):
        return _google_cse_search(company_name, max_results)
    elif os.getenv("SERPAPI_KEY"):
        return _serpapi_search(company_name, max_results)
    else:
        return [{"title": "News search not configured", "snippet": "Set GOOGLE_CSE_API_KEY+GOOGLE_CSE_ID or SERPAPI_KEY to enable news.", "url": ""}]


def _google_cse_search(company_name: str, max_results: int) -> list[dict]:
    resp = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={
            "key": os.getenv("GOOGLE_CSE_API_KEY"),
            "cx": os.getenv("GOOGLE_CSE_ID"),
            "q": f"{company_name} news",
            "num": max_results,
            "sort": "date",
            "dateRestrict": "m3",  # last 3 months
        },
        timeout=15,
    )
    if resp.status_code != 200:
        return []

    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "url": item.get("link", ""),
            "date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", ""),
        }
        for item in resp.json().get("items", [])
    ]


def _serpapi_search(company_name: str, max_results: int) -> list[dict]:
    resp = requests.get(
        "https://serpapi.com/search",
        params={
            "api_key": os.getenv("SERPAPI_KEY"),
            "q": f"{company_name} news",
            "engine": "google",
            "tbm": "nws",
            "num": max_results,
            "tbs": "qdr:m3",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        return []

    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "url": r.get("link", ""),
            "date": r.get("date", ""),
        }
        for r in resp.json().get("news_results", [])[:max_results]
    ]
