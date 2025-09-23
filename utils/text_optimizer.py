import re
from typing import List, Dict
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter



class TextOptimizer:
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

    def display_optimization_results(self, optimized_result: dict):
        """Display optimization statistics in a formatted way."""
        context = optimized_result["text"]
        opt_info = optimized_result["optimization_info"]
        
        token_change = opt_info.get('optimized_tokens', 0) - opt_info.get('original_tokens', 0)
        change_percentage = (opt_info.get('optimized_tokens', 0) - opt_info.get('original_tokens', 0)) / opt_info.get('original_tokens', 0) * 100
        cost_change = opt_info.get('optimized_cost', 0) - opt_info.get('original_cost', 0)
        
        print(f"\n{'='*60}")
        print(f"📄 EXTRACTION RESULTS")
        print(f"{'='*60}")
        
        print(f"\n📄 Optimized Text Preview:")
        print("-" * 60)
        print(context)
        print("-" * 60 + "\n")
        
        print("-" * 60)
        print(f"✅ Strategy: {opt_info.get('strategy', 'none')}")
        print(f"📊 Tokens Changed: {opt_info.get('original_tokens', 0):,} -> {opt_info.get('optimized_tokens', 0):,} ({token_change:,}) ({change_percentage:.1f}%)")
        print(f"💰 Cost Change: ${opt_info.get('original_cost', 0):.4f} -> ${opt_info.get('optimized_cost', 0):.4f} (${cost_change:.4f})")
        print("-" * 60)
    
    
    
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
    
    
    
    def optimize_markdown(self, content: str, include_sections: List[str] = ["abstract", "introduction", "methodology", "conclusion"], token_limit: int = 4000):
        section_mapping = {
            'abstract': ['abstract', 'summary'],
            'introduction': ['introduction', 'intro'],
            'methodology': ['methods', 'methodology', 'method', 'approach', 'framework', 'model'],
            'results': ['results', 'experiments', 'evaluation', 'findings'],
            'discussion': ['discussion', 'analysis'],
            'conclusion': ['conclusion', 'conclusions', 'summary'],
            'related_work': ['related work', 'background', 'literature review']
        }
        # 1. Get all markdown sections
        pattern = r'^(#+.*?)$(.*?)(?=^#+.*$|\Z)'
        matches = re.findall(pattern, content, flags=re.MULTILINE | re.DOTALL)
        sections = {}
        for header, content_part in matches:
            # Clean up the header and content
            header_clean = header.strip()
            content_clean = content_part.strip()
            # Extract title from header (remove # symbols and numbers)
            title = re.sub(r'^#+\s*(?:\d+\.?\s+)?', '', header_clean).strip().lower()
            # Store with full content including header
            sections[title] = f"{header_clean}\n{content_clean}"
        
        # 2. Extract only the requested sections
        include_sections = [alias for section in include_sections 
                            for alias in section_mapping[section]]
        extracted_sections = {}
        for section_name in include_sections:
            section_key = section_name.lower()
            if section_key in sections:
                extracted_sections[section_name] = sections[section_key]
        
        # 3. Join the sections if there are any, otherwise fallback to truncate
        if len(extracted_sections) == 0:
            optimized_text = self.simple_truncate(content, token_limit)        # truncate the content
            strategy = "simple truncate"
        else:
            optimized_text = '\n'.join(extracted_sections.values())
            optimized_text = self.simple_truncate(optimized_text, token_limit) # truncate the content
            strategy = "selected sections with truncate"
        
        return {
            "text": optimized_text,
            "optimization_info": {
                "strategy": strategy,
                "original_tokens": self.count_tokens(content),
                "optimized_tokens": self.count_tokens(optimized_text),
                "original_cost": self.estimate_cost(content)["total_cost"],
                "optimized_cost": self.estimate_cost(optimized_text)["total_cost"],
            }
        }