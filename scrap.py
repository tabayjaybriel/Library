# app.py
from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

# Create the Flask app instance.
# This object is what runs your web server.
app = Flask(__name__)

# IMPORTANT: This is for educational purposes. Scraping Google Scholar may violate
# their terms of service. Be sure to check the robots.txt file and terms of use
# of any website you intend to scrape.

def perform_scholar_search(query_string):
    """
    Performs a search on Google Scholar using the user's query and returns the
    parsed HTML. This function is an improved version of your original one.

    Args:
        query_string (str): The search query provided by the user.

    Returns:
        bs4.BeautifulSoup: A BeautifulSoup object containing the parsed HTML.
    """
    # Sanitize the query by replacing spaces with '+' for the URL.
    sanitized_query = query_string.replace(' ', '+')
    
    # Define the dynamic URL for Google Scholar, passing the user's query.
    search_url = f"https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q={sanitized_query}"

    try:
        # Use a user-agent to mimic a browser, which is a common practice.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        # Send an HTTP GET request to the URL with a timeout.
        response = requests.get(search_url, headers=headers, timeout=10)
        
        # Raise an exception for bad status codes (4xx or 5xx).
        response.raise_for_status()

        # Parse the HTML content.
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Successfully fetched and parsed content for query: '{query_string}'")
        
        return soup

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def process_scholar_results(soup):
    """
    Processes the parsed HTML to extract relevant information from Google Scholar.
    The CSS selectors have been updated to match the current Google Scholar structure.

    Args:
        soup (bs4.BeautifulSoup): The parsed HTML from the search result page.

    Returns:
        list: A list of dictionaries, where each dictionary represents a search result.
    """
    if not soup:
        return []

    results = []
    # Find all the div elements that contain a Google Scholar search result.
    search_results = soup.find_all('div', class_='gs_r')

    if not search_results:
        print("No search results found with the specified selector.")
        return []
        
    for result in search_results:
        title_tag = result.find('h3', class_='gs_rt')
        link_tag = title_tag.find('a') if title_tag else None
        citation_tag = result.find('div', class_='gs_a')
        snippet_tag = result.find('div', class_='gs_rs')

        title = title_tag.get_text() if title_tag else "No Title Found"
        link = link_tag['href'] if link_tag and 'href' in link_tag.attrs else "#"
        citation = citation_tag.get_text() if citation_tag else "No Citation Found"
        # The snippet text is often prefixed with '... ', so we remove it.
        snippet = snippet_tag.get_text().strip().replace('... ', '', 1) if snippet_tag else "No Snippet Found"

        results.append({
            'title': title,
            'link': link,
            'citation': citation,
            'snippet': snippet
        })
        
    return results

@app.route('/')
def index():
    """
    This is the main route that serves the initial HTML page with the form.
    """
    return render_template('home.html')

@app.route('/search', methods=['POST'])
def search_handler():
    """
    This route handles the form submission from the HTML page and now
    renders the results on 'scrapresult.html'.
    """
    user_query = request.form.get('query')
    
    if not user_query:
        return "No query provided.", 400

    soup_object = perform_scholar_search(user_query)

    if soup_object:
        search_results_list = process_scholar_results(soup_object)
        
        # Pass the results to the new 'scrapresult.html' template.
        return render_template('scrapresult.html', results=search_results_list, query=user_query)
    else:
        # Handle the case where the search failed.
        return render_template('scrapresult.html', results=[], query=user_query, error=True)

# This block ensures the Flask app runs only when this script is executed directly.
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
