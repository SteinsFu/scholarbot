import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests
from dotenv import load_dotenv
from langdetect import detect
from markdown_to_mrkdwn import SlackMarkdownConverter
from urllib.parse import urlparse, unquote



load_dotenv()
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
bot_user_id = app.client.auth_test()["user_id"]

lang_maps = {
    'ja': 'Japanese',
    'en': 'English',
    'zh': 'Chinese',
    # add more languages here
}

# ===== Semantic Scholar API =====
def get_doi_from_url(url: str) -> str | None:
    # decode percent-encoding and get path
    path = unquote(urlparse(url).path)
    # regex for DOI
    doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
    match = re.search(doi_pattern, path, re.I)
    if match:
        return match.group(0)
    return None


def get_arxiv_id_from_url(url: str) -> str | None:
    """
    Extract ArXiv paper ID from ArXiv URL and return it in the format "ArXiv:XXXX.XXXXX"
    
    Supports various ArXiv URL formats:
    - https://arxiv.org/abs/1805.02262
    - https://arxiv.org/pdf/1805.02262.pdf
    - https://arxiv.org/abs/2101.00001v1
    - http://arxiv.org/abs/math/0309285
    
    Args:
        url (str): ArXiv URL
        
    Returns:
        str | None: Paper ID in format "ArXiv:XXXX.XXXXX" or None if not found
    """
    # decode percent-encoding and get path
    path = unquote(urlparse(url).path)
    
    # ArXiv ID patterns:
    # New format: YYMM.NNNNN (e.g., 1805.02262)
    # Old format: subject-class/YYMMnnn (e.g., math/0309285)
    
    # Pattern for new format (post-2007): 4 digits + dot + 4-5 digits + optional version
    new_pattern = r'(\d{4}\.\d{4,5})(?:v\d+)?'
    
    # Pattern for old format (pre-2007): subject/YYMMnnn
    old_pattern = r'([a-z-]+/\d{7})'
    
    # Try new format first
    match = re.search(new_pattern, path)
    if match:
        return f"ArXiv:{match.group(1)}"
    
    # Try old format
    match = re.search(old_pattern, path, re.I)
    if match:
        return f"ArXiv:{match.group(1)}"
    
    return None


def get_paperid_from_doi(doi):
    base_url = "https://api.semanticscholar.org/graph/v1/paper/"
    paper_id_param = f"DOI:{doi}"
    fields = "paperId"  # only need the paperId field in the response
    url = f"{base_url}{paper_id_param}?fields={fields}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        if data and "paperId" in data:
            return data["paperId"]
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None


def parse_event(event):
    query_raw = event['text'].replace(f"<@{bot_user_id}>", "").strip()  # remove the mention part    
    
    # Find all URLs in the query
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
    urls = re.findall(url_pattern, query_raw)
    pdf_url = urls[0] if urls else None  # Take the first URL found, or None if no URLs
    
    # Remove all URLs from the query (and clean up extra whitespace)
    query = re.sub(url_pattern, '', query_raw).strip()
    query = ' '.join(query.split())
    
    pdf_file = None                                         # TODO: implement this
    language_code = detect(query) if query else 'en'
    language = lang_maps.get(language_code, 'English')
    return query, pdf_url, pdf_file, language


def parse_response(response):
    response_data = response.json()
    if 'answer' not in response_data:
        return None
    converter = SlackMarkdownConverter()
    mrkdwn_text = converter.convert(response_data['answer'])
    return mrkdwn_text


def search_related_papers_semantic(pdf_url, limit=10):
    if 'arxiv' in pdf_url:
        paper_id = get_arxiv_id_from_url(pdf_url)
        print(f"Paper ID: {paper_id}")
    else:
        doi = get_doi_from_url(pdf_url)
        print(f"DOI: {doi}")
        paper_id = get_paperid_from_doi(doi)
        print(f"Paper ID: {paper_id}")
    url = "https://api.semanticscholar.org/recommendations/v1/papers"
    body = {
        "positivePaperIds": [paper_id],
        "negativePaperIds": []
    }
    r = requests.post(url, params={"fields": "title,year,url,authors"}, json=body)
    data = r.json()
    return data.get("recommendedPapers", [])[:limit]



@app.event("app_mention")
def handle_app_mention(event, say):
    print(event)
    if event and 'text' in event:
        say("Processing your request...")
        dify_api_key = os.environ["DIFY_API_KEY"]
        url = 'http://localhost/v1/chat-messages'   # Dify API endpoint
        user = event['user']
        
        # parse parameters from the query
        query, pdf_url, pdf_file, language = parse_event(event)
    
        related_papers = search_related_papers_semantic(pdf_url)
        print(f"Related Papers: {related_papers}")
        say(f"Related Papers: {related_papers}")
        
        # # Construct the headers and data
        # headers = {
        #     'Authorization': f'Bearer {dify_api_key}',
        #     'Content-Type': 'application/json'
        # }
        # data = {
        #     'query': query,
        #     'inputs': {'pdf_url': pdf_url, 'pdf_file': pdf_file, 'language': language},
        #     'response_mode': 'blocking',
        #     'user': user,
        #     'conversation_id': '',
        # }
        # response = requests.post(url, headers=headers, json=data)
        # # parse the response
        # answer = parse_response(response)
        # if answer:
        #     say(answer)
        # else:
        #     say(f"Unexpected response from Dify API: {response}")
    else:
        say("Cannot get the message content.")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
