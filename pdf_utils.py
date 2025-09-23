import io
import requests
from PyPDF2 import PdfReader
from typing import Optional, Dict, Any
from text_optimizer import TextOptimizer


def pdf_url_to_text(pdf_url: str, optimize: bool = True, strategy: str = "auto", max_tokens: int = 4000) -> Dict[str, Any]:
    """
    Convert a PDF URL to text using PyPDF2 with optional optimization for API usage.
    
    Args:
        pdf_url (str): URL of the PDF file to extract text from
        optimize (bool): Whether to optimize text for reduced token usage
        strategy (str): Optimization strategy ("auto", "smart", "sections", "truncate", "chunk", "none")
        max_tokens (int): Maximum tokens for optimized output
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - text: Extracted (and optionally optimized) text
            - original_text: Original unprocessed text
            - optimization_info: Details about optimization applied (if any)
        
    Raises:
        requests.RequestException: If the PDF cannot be downloaded
        Exception: If the PDF cannot be processed
    """
    try:
        # Download the PDF from the URL
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Create a file-like object from the downloaded content
        pdf_file = io.BytesIO(response.content)
        
        # Create a PDF reader object
        pdf_reader = PdfReader(pdf_file)
        
        # Extract text from all pages
        original_text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            original_text += page.extract_text() + "\n"
        
        original_text = original_text.strip()
        
        # If optimization is disabled, return original text
        if not optimize:
            return {
                "text": original_text,
                "original_text": original_text,
                "optimization_info": {"strategy": "none", "optimized": False}
            }
        
        # Initialize text optimizer
        optimizer = TextOptimizer()
        
        # Auto-select strategy if requested
        if strategy == "auto":
            strategy = optimizer.recommend_strategy(original_text)
        
        # Skip optimization if not needed
        if strategy == "none":
            return {
                "text": original_text,
                "original_text": original_text,
                "optimization_info": {"strategy": "none", "optimized": False}
            }
        
        # Apply optimization
        optimization_result = optimizer.optimize_text(original_text, strategy, max_tokens)
        
        return {
            "text": optimization_result.get("optimized_text", original_text),
            "original_text": original_text,
            "optimization_info": optimization_result | {"optimized": True}
        }
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Failed to download PDF from {pdf_url}: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def pdf_url_to_text_simple(pdf_url: str) -> str:
    """
    Simple version that returns just the text string for backward compatibility.
    
    Args:
        pdf_url (str): URL of the PDF file to extract text from
        
    Returns:
        str: Extracted text from the PDF
    """
    result = pdf_url_to_text(pdf_url, optimize=False)
    return result["text"]
