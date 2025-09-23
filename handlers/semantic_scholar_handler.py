import requests
from urllib.parse import urlparse, unquote
import re
from urllib3 import response



class SemanticScholarHandler:
    def __init__(self):
        self.paper_url = "https://api.semanticscholar.org/graph/v1/paper/"
        self.recommendations_url = "https://api.semanticscholar.org/recommendations/v1/papers"
        self.fields = "paperId"
        

    def get_doi_from_url(self, url: str) -> str | None:
        # decode percent-encoding and get path
        path = unquote(urlparse(url).path)
        # regex for DOI
        doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
        match = re.search(doi_pattern, path, re.I)
        if match:
            return match.group(0)
        return None


    def get_arxiv_id_from_url(self, url: str) -> str | None:
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


    def get_paper(self, url: str):
        # get the paper id parameter
        if 'arxiv' in url:
            paper_id_param = self.get_arxiv_id_from_url(url)
        else:
            doi = self.get_doi_from_url(url)
            paper_id_param = f"DOI:{doi}"
        # get the paper meta data
        fields = "paperId,title,year,authors,abstract"
        url = f"{self.paper_url}{paper_id_param}?fields={fields}"
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data


    def get_recommendations(self, paper_id, limit=10):
        body = {
            "positivePaperIds": [paper_id],
            "negativePaperIds": []
        }
        response = requests.post(self.recommendations_url, params={"fields": "title,year,url,authors,abstract,publicationVenue"}, json=body)
        data = response.json()
        return data.get("recommendedPapers", [])[:limit]