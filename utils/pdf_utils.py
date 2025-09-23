import io
import os
import re
import requests
import tempfile
from typing import Optional, Dict, Any, Tuple, List
import PyPDF2
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter


"""
This module is not used currently.
"""


# Helper function to extract bookmarks from the PDF
def bookmark_dict(bookmark_list, reader):
    result = {}
    for item in bookmark_list:
        if isinstance(item, list):
            # recursive call for nested bookmarks
            result.update(bookmark_dict(item, reader))
        else:
            try:
                page_num = reader.get_destination_page_number(item) + 1  # 1-indexed
                result[page_num] = item.title
            except Exception:
                # Skip bookmarks that can't be processed
                pass
    return result


class PDFTextOptimizer:
    def __init__(self, max_tokens_per_chunk: int = 4000):
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.encoding = tiktoken.encoding_for_model("gpt-4")  # Use gpt-4 encoding as fallback
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens_per_chunk * 3,  # Approximate character to token ratio
            chunk_overlap=200,
            length_function=self.count_tokens,
            separators=["\n\n", "\n", ".", "!", "?", ";", " ", ""]
        )
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self.encoding.encode(text))
    
    def estimate_cost(self, text: str, input_cost_per_1k: float = 0.0025, output_cost_per_1k: float = 0.01) -> Dict[str, float]:
        """
        Estimate the cost of processing text with ChatGPT API.
        
        Args:
            text: Input text to analyze
            input_cost_per_1k: Cost per 1000 input tokens (default for GPT-4o)
            output_cost_per_1k: Cost per 1000 output tokens (default for GPT-4o)
            
        Returns:
            Dictionary with cost estimates
        """
        input_tokens = self.count_tokens(text)
        estimated_output_tokens = min(input_tokens * 0.3, 4000)  # Estimate 30% of input or max 4k
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (estimated_output_tokens / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and preprocess PDF text to remove noise and redundancy."""
        # Remove common PDF artifacts first
        text = re.sub(r'\f', ' ', text)  # Form feed characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)  # Control characters
        
        # Clean up whitespace but preserve line structure for section detection
        # Replace multiple spaces with single space, but keep newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs -> single space
        text = re.sub(r'\n[ \t]+', '\n', text)  # Remove leading spaces on lines
        text = re.sub(r'[ \t]+\n', '\n', text)  # Remove trailing spaces on lines
        text = re.sub(r'\n{3,}', '\n\n', text)  # Reduce multiple newlines to double
        
        # Remove repeated page headers/footers (simple heuristic)
        lines = text.split('\n')
        cleaned_lines = []
        prev_line = ""
        repetition_count = 0
        
        for line in lines:
            line = line.strip()
            if line == prev_line and len(line) < 100:  # Likely header/footer
                repetition_count += 1
                if repetition_count < 3:  # Keep first few occurrences
                    cleaned_lines.append(line)
            else:
                repetition_count = 0
                cleaned_lines.append(line)
            prev_line = line
        
        # Remove excessive references section (often very long and less useful for summaries)
        text = '\n'.join(cleaned_lines)
        
        # Find and truncate references section if it's too long
        ref_patterns = [
            r'\n\s*REFERENCES?\s*\n',
            r'\n\s*Bibliography\s*\n',
            r'\n\s*References and Notes\s*\n'
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                before_refs = text[:match.start()]
                refs_section = text[match.start():]
                
                # If references section is more than 20% of total text, truncate it
                if len(refs_section) > len(text) * 0.2:
                    # Keep only first part of references
                    truncated_refs = refs_section[:min(1000, len(refs_section)//3)]
                    text = before_refs + truncated_refs + "\n\n[References section truncated for brevity]"
                break
        
        return text.strip()




    def extract_all_sections(self, pdf_path_or_url: str) -> Dict[str, str]:
        """
        Extract sections from PDF using bookmark structure and text content.
        
        Args:
            pdf_path_or_url: Path or URL to the PDF file
        Returns:
            Dictionary mapping section names to their content
        """
        def _process_pdf(pdf_path: str) -> Dict[str, str]:
            """Inner function to process the PDF once we have a valid path."""
            # Read PDF to get page-wise content and bookmarks
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # 1. Extract bookmarks from the PDF
                bookmarks = {}
                if hasattr(reader, 'outline') and reader.outline:
                    bookmarks = bookmark_dict(reader.outline, reader)
                
                # 2. Extract text from the PDF
                pages_text = []
                for page in reader.pages:
                    pages_text.append(page.extract_text())
            
            # Map bookmark titles to standard section names
            section_mapping = {
                'abstract': ['abstract', 'summary'],
                'introduction': ['introduction', 'intro'],
                'methodology': ['methods', 'methodology', 'method', 'approach', 'framework', 'model'],
                'results': ['results', 'experiments', 'evaluation', 'findings'],
                'discussion': ['discussion', 'analysis'],
                'conclusion': ['conclusion', 'conclusions', 'summary'],
                'related_work': ['related work', 'background', 'literature review']
            }
            
            # Construct sections
            sections = {}
            sorted_bookmarks = sorted(bookmarks.items())
            for i, (page_num, title) in enumerate(sorted_bookmarks):
                # Normalize title for matching
                title_lower = title.lower().strip()
                
                # Find which section this bookmark belongs to
                section_type = None
                for section, keywords in section_mapping.items():
                    if any(keyword in title_lower for keyword in keywords):
                        section_type = section
                        break
                
                if section_type:
                    # Extract content from this page to the next bookmark or end
                    start_page = page_num - 1  # Convert to 0-indexed
                    end_page = len(pages_text)
                    
                    # Find the next bookmark to determine where this section ends
                    if i + 1 < len(sorted_bookmarks):
                        next_page = sorted_bookmarks[i + 1][0] - 1  # Convert to 0-indexed
                        end_page = next_page
                    
                    # Combine pages for this section
                    section_content = ""
                    for page_idx in range(start_page, min(end_page, len(pages_text))):
                        if page_idx < len(pages_text):
                            section_content += pages_text[page_idx] + "\n"
                    
                    sections[section_type] = section_content.strip()
            
            # If no bookmarks found, return all text as introduction
            if not sections:
                all_text = "\n".join(pages_text)
                sections = {'introduction': all_text}
            
            return sections
        
        # Handle local files vs URLs
        if os.path.exists(pdf_path_or_url):
            return _process_pdf(pdf_path_or_url)
        else:
            # Download URL to temporary file and process within context
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_url = pdf_path_or_url
                pdf_path = os.path.join(temp_dir, "temp_paper.pdf")
                response = requests.get(pdf_url, timeout=30)
                response.raise_for_status()
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                
                return _process_pdf(pdf_path)
    
    
    def optimize_and_join_sections(
        self, 
        sections: Dict[str, str], 
        include_sections: List[str] = ['abstract', 'introduction', 'methodology', 'conclusion'],
        target_tokens: int = 4000,
    ) -> Dict[str, str]:
        """
        Optimize the sections of a PDF file.
        
        Args:
            sections: Dictionary of sections to optimize
            include_sections: List of sections to include in the output
            target_tokens: Target token count
        Returns:
            Optimized sections
        """
        text = '\n'.join([sections[section] for section in include_sections])
        # current_tokens = self.count_tokens(text)
        # if current_tokens <= target_tokens:
        #     return text
        
        # TODO: fixed sections and implement this
        
        return text
    
    def read_pdf(
        self, 
        pdf_path_or_url: str, 
        include_sections: List[str] = ['abstract', 'introduction', 'methodology', 'conclusion'],
        target_tokens: int = 4000,
    ) -> str:
        """
        Read a PDF file and return the text content.
        
        Args:
            pdf_path_or_url: Path or URL to the PDF file
            include_sections: List of sections to include in the output
        Returns:
            Text content of the PDF
        """
        sections = self.extract_all_sections(pdf_path_or_url)
        text = self.optimize_and_join_sections(sections, include_sections, target_tokens)
        return text





