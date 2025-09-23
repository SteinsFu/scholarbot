import requests
from dotenv import load_dotenv
import os
import re
from typing import List, Text

class JinaHandler:
    def __init__(self):
        load_dotenv()
        self.jina_api_key = os.environ.get("JINA_API_KEY")
        self.jina_api_url = "https://r.jina.ai/"
    
    def fetch_url(self, url: str):
        headers = {
            "Authorization": f"Bearer {self.jina_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url
        }
        response = requests.post(self.jina_api_url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.text
    
    
