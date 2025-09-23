import requests
from dotenv import load_dotenv
import os
import re
import base64
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
    
    def fetch_pdf_file(self, pdf_content: bytes, url: str = ""):
        """
        Send PDF file content as base64 to Jina API for text extraction
        
        Args:
            pdf_content: Raw PDF file content as bytes
            url: Optional URL for reference (can be empty for uploaded files)
            
        Returns:
            str: Extracted text content from the PDF
        """
        headers = {
            "Authorization": f"Bearer {self.jina_api_key}",
            "Content-Type": "application/json"
        }
        
        # Encode PDF content to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        payload = {
            "url": url or "https://uploaded-file.pdf",  # Jina needs a URL field, use placeholder for uploads
            "pdf": pdf_base64
        }
        
        response = requests.post(self.jina_api_url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.text
    
