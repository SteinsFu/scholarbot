import re
import tiktoken
from typing import List, Dict, Optional, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import os

class TextOptimizer:
    """
    Utility class to optimize PDF text for efficient ChatGPT API usage.
    Includes token counting, text chunking, and intelligent preprocessing.
    """
    
    def __init__(self, model_name: str = "gpt-4o", max_tokens_per_chunk: int = 4000):
        load_dotenv()
        self.model_name = model_name
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.encoding = tiktoken.encoding_for_model("gpt-4")  # Use gpt-4 encoding as fallback
        
        # Initialize the model for summarization
        self.model = init_chat_model(model_name, model_provider="openai")
        
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
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'\f', ' ', text)  # Form feed characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)  # Control characters
        
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
    
    def extract_key_sections(self, text: str, debug: bool = False) -> Dict[str, str]:
        """Extract key sections from academic paper text."""
        sections = {}
        
        if debug:
            print("DEBUG: Looking for sections in text...")
            print(f"DEBUG: Text length: {len(text)} characters")
            print(f"DEBUG: First 500 characters:\n{text[:500]}")
            print("=" * 50)
        
        # More flexible section patterns that handle various formats
        section_patterns = {
            'abstract': [
                r'(?:^|\n)\s*(?:ABSTRACT|Abstract|abstract)\s*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|Keywords?|KEYWORDS?|Introduction|INTRODUCTION|\d+\.|\d+\s+[A-Z]|\Z))',
                r'(?:^|\n)\s*(?:ABSTRACT|Abstract|abstract)\s*[:\-]?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|Keywords?|KEYWORDS?|Introduction|INTRODUCTION|\d+\.|\d+\s+[A-Z]|\Z))',
                r'(?:^|\n)\s*(?:ABSTRACT|Abstract|abstract)\s+(.*?)(?=\n\s*(?:Keywords?|KEYWORDS?|Introduction|INTRODUCTION|\d+\.|\d+\s+[A-Z]|[A-Z][A-Z\s]*[A-Z]|\Z))'
            ],
            'introduction': [
                r'(?:^|\n)\s*(?:1\.?\s*)?(?:INTRODUCTION|Introduction|introduction)\s*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|\d+\.|\d+\s+[A-Z]|\Z))',
                r'(?:^|\n)\s*(?:1\.?\s*)?(?:INTRODUCTION|Introduction|introduction)\s*[:\-]?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|\d+\.|\d+\s+[A-Z]|\Z))',
                r'(?:^|\n)\s*(?:1\.\s+)?(?:INTRODUCTION|Introduction|introduction)\s+(.*?)(?=\n\s*(?:\d+\.|\d+\s+[A-Z]|[A-Z][A-Z\s]*[A-Z]|\Z))'
            ],
            'conclusion': [
                r'(?:^|\n)\s*(?:\d+\.?\s*)?(?:CONCLUSION|Conclusion|conclusion|CONCLUSIONS|Conclusions|conclusions)\s*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|REFERENCES?|References?|Bibliography|BIBLIOGRAPHY|\Z))',
                r'(?:^|\n)\s*(?:\d+\.?\s*)?(?:CONCLUSION|Conclusion|conclusion|CONCLUSIONS|Conclusions|conclusions)\s*[:\-]?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|REFERENCES?|References?|Bibliography|BIBLIOGRAPHY|\Z))',
                r'(?:^|\n)\s*(?:\d+\.\s+)?(?:CONCLUSION|Conclusion|conclusion|CONCLUSIONS|Conclusions|conclusions)\s+(.*?)(?=\n\s*(?:REFERENCES?|References?|Bibliography|BIBLIOGRAPHY|[A-Z][A-Z\s]*[A-Z]|\Z))'
            ],
            'methodology': [
                r'(?:^|\n)\s*(?:\d+\.?\s*)?(?:METHODOLOGY|Methodology|methodology|METHODS|Methods|methods|METHOD|Method|method)\s*\n(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|\d+\.|\d+\s+[A-Z]|\Z))',
                r'(?:^|\n)\s*(?:\d+\.?\s*)?(?:METHODOLOGY|Methodology|methodology|METHODS|Methods|methods|METHOD|Method|method)\s*[:\-]?\s*(.*?)(?=\n\s*(?:[A-Z][A-Z\s]*[A-Z]|\d+\.|\d+\s+[A-Z]|\Z))',
                r'(?:^|\n)\s*(?:\d+\.\s+)?(?:METHODOLOGY|Methodology|methodology|METHODS|Methods|methods|METHOD|Method|method)\s+(.*?)(?=\n\s*(?:\d+\.|\d+\s+[A-Z]|[A-Z][A-Z\s]*[A-Z]|\Z))'
            ]
        }
        
        # Try each pattern for each section
        for section_name, patterns in section_patterns.items():
            found = False
            for i, pattern in enumerate(patterns):
                if debug:
                    print(f"DEBUG: Trying {section_name} pattern {i+1}")
                
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    section_text = match.group(1).strip()
                    # Clean up section text
                    section_text = re.sub(r'\s+', ' ', section_text)
                    sections[section_name] = section_text[:2000]  # Limit section length
                    
                    if debug:
                        print(f"DEBUG: Found {section_name}! Length: {len(section_text)} chars")
                        print(f"DEBUG: Preview: {section_text[:100]}...")
                    
                    found = True
                    break
            
            if debug and not found:
                print(f"DEBUG: No match found for {section_name}")
        
        if debug:
            print(f"DEBUG: Total sections found: {len(sections)}")
            print(f"DEBUG: Sections: {list(sections.keys())}")
        
        return sections
    
    def analyze_text_structure(self, text: str) -> Dict[str, any]:
        """Analyze text structure to identify potential sections and their patterns."""
        analysis = {
            "total_length": len(text),
            "total_lines": len(text.split('\n')),
            "potential_headers": [],
            "numbered_sections": [],
            "all_caps_lines": [],
            "title_case_lines": []
        }
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
                
            # Look for potential headers (short lines that might be section titles)
            if 5 <= len(stripped) <= 50:
                # Check for common section keywords
                section_keywords = [
                    'abstract', 'introduction', 'methodology', 'methods', 'method',
                    'results', 'result', 'discussion', 'conclusion', 'conclusions',
                    'references', 'bibliography', 'acknowledgment', 'acknowledgments',
                    'related work', 'background', 'literature review', 'experimental',
                    'evaluation', 'implementation', 'analysis', 'future work'
                ]
                
                if any(keyword in stripped.lower() for keyword in section_keywords):
                    analysis["potential_headers"].append({
                        "line": i,
                        "text": stripped,
                        "keywords_found": [kw for kw in section_keywords if kw in stripped.lower()]
                    })
            
            # Look for numbered sections
            if re.match(r'^\s*\d+\.?\s+[A-Za-z]', stripped):
                analysis["numbered_sections"].append({
                    "line": i,
                    "text": stripped[:50] + "..." if len(stripped) > 50 else stripped
                })
            
            # Look for all caps lines (potential headers)
            if stripped.isupper() and 3 <= len(stripped) <= 30:
                analysis["all_caps_lines"].append({
                    "line": i,
                    "text": stripped
                })
            
            # Look for title case lines (potential headers)
            if stripped.istitle() and 5 <= len(stripped) <= 40:
                analysis["title_case_lines"].append({
                    "line": i,
                    "text": stripped
                })
        
        return analysis
    
    def create_smart_summary(self, text: str, target_tokens: int = 2000) -> str:
        """
        Create an intelligent summary that preserves key information while reducing token count.
        """
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= target_tokens:
            return text
        
        # Try to extract key sections first
        sections = self.extract_key_sections(text)
        
        if sections:
            # Prioritize important sections
            priority_order = ['abstract', 'introduction', 'methodology', 'conclusion']
            summary_parts = []
            
            for section in priority_order:
                if section in sections:
                    summary_parts.append(f"**{section.title()}:**\n{sections[section]}\n")
            
            if summary_parts:
                summary = '\n'.join(summary_parts)
                if self.count_tokens(summary) <= target_tokens:
                    return summary
        return None
    
    def create_ai_summary(self, text: str, target_tokens: int = 2000) -> str:
        """
        Create a summary of the text using the AI model.
        """
        summarization_prompt = f"""
        Please create a concise summary of this academic paper that preserves the most important information.
        Focus on: research objectives, methodology, key findings, and conclusions.
        Target length: approximately {target_tokens} tokens.
        
        Text to summarize:
        {text[:10000]}  # Limit input to avoid token issues
        """
        
        try:
            response = self.model.invoke([HumanMessage(content=summarization_prompt)])
            return response.content
        except Exception as e:
            print(f"AI summarization failed: {e}")
            # Fallback: simple truncation with key sections
            return self.simple_truncate(text, target_tokens)
    
    def simple_truncate(self, text: str, target_tokens: int) -> str:
        """Simple truncation strategy that preserves beginning and end of text."""
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= target_tokens:
            return text
        
        # Take 70% from beginning, 30% from end
        chars_ratio = target_tokens / current_tokens
        total_chars = len(text)
        
        beginning_chars = int(total_chars * chars_ratio * 0.7)
        ending_chars = int(total_chars * chars_ratio * 0.3)
        
        beginning = text[:beginning_chars]
        ending = text[-ending_chars:]
        
        return f"{beginning}\n\n[... content truncated ...]\n\n{ending}"
    
    def optimize_text(self, text: str, strategy: str = "smart", target_tokens: int = 4000) -> Dict[str, any]:
        """
        Main optimization function that applies various strategies to reduce token usage.
        
        Args:
            text: Input text to optimize
            strategy: Optimization strategy ("smart", "sections", "truncate", "chunk")
            target_tokens: Target token count
            
        Returns:
            Dictionary with optimized text and metadata
        """
        original_tokens = self.count_tokens(text)
        original_cost = self.estimate_cost(text)
        
        # Clean the text first
        cleaned_text = self.clean_text(text)
        
        used_ai = False
        if strategy == "smart":
            optimized_text = self.create_smart_summary(cleaned_text, target_tokens)
            if optimized_text is None:
                optimized_text = self.create_ai_summary(cleaned_text, target_tokens)
                used_ai = True
        elif strategy == "sections":
            sections = self.extract_key_sections(cleaned_text)
            if sections:
                section_texts = [f"**{k.title()}:** {v}" for k, v in sections.items()]
                optimized_text = '\n\n'.join(section_texts)
            else:
                optimized_text = self.simple_truncate(cleaned_text, target_tokens)
        elif strategy == "truncate":
            optimized_text = self.simple_truncate(cleaned_text, target_tokens)
        elif strategy == "chunk":
            # Return chunks instead of single text
            chunks = self.text_splitter.split_text(cleaned_text)
            return {
                "strategy": strategy,
                "original_tokens": original_tokens,
                "chunks": chunks,
                "chunk_count": len(chunks),
                "original_cost": original_cost,
                "estimated_savings": "Process chunks individually",
                "used_ai": used_ai
            }
        else:
            optimized_text = cleaned_text
        
        optimized_tokens = self.count_tokens(optimized_text)
        optimized_cost = self.estimate_cost(optimized_text)
        
        return {
            "strategy": strategy,
            "original_text": text,
            "optimized_text": optimized_text,
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "token_reduction": original_tokens - optimized_tokens,
            "reduction_percentage": ((original_tokens - optimized_tokens) / original_tokens) * 100,
            "original_cost": original_cost,
            "optimized_cost": optimized_cost,
            "cost_savings": original_cost["total_cost"] - optimized_cost["total_cost"],
            "used_ai": used_ai
        }
    
    def recommend_strategy(self, text: str) -> str:
        """Recommend the best optimization strategy based on text characteristics."""
        token_count = self.count_tokens(text)
        
        if token_count <= 2000:
            return "none"  # No optimization needed
        elif token_count <= 8000:
            return "smart"  # Intelligent summarization
        elif token_count <= 20000:
            return "sections"  # Extract key sections
        else:
            return "chunk"  # Process in chunks
