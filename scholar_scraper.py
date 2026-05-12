import requests

def scholar_scrape(query, page=1, per_page=25):
    """
    Uses OpenAlex API to fetch scholarly results reliably and for free.
    """
    try:
        # OpenAlex doesn't require an API key for the "polite" pool, 
        # but you can add your email to the params if you want better performance.
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "page": page,
            "per-page": per_page,
            "sort": "publication_year:desc"
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []

        for item in data.get("results", []):
            # Format authors from the authorships list
            authors_list = [a.get("author", {}).get("display_name", "Unknown") 
                           for a in item.get("authorships", [])]
            authors_str = ", ".join(authors_list) if authors_list else "Unknown Author"
            
            # Extract the best possible link (Landing page or DOI)
            link = item.get("primary_location", {}).get("landing_page_url") or item.get("doi") or "#"

            results.append({
                "title": item.get("title", "No Title"),
                "author": authors_str,
                "year": item.get("publication_year"),
                "link": link,
                "summary": f" Type: {item.get('type', 'Work')}",
                "source_label": "OpenAlex"
            })
        return results
    except Exception as e:
        print(f"[ERROR] OpenAlex search failed: {e}")
        return []