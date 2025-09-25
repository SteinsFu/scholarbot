"""
Paper processing service that handles the core logic for analyzing papers.
Extracted from the original Slack bot to be reusable across different interfaces.
"""
import os
import re
from typing import Dict, Optional, Tuple, Any
from langdetect import detect
from markdown_to_mrkdwn import SlackMarkdownConverter
from urllib.parse import urlparse, unquote

from handlers.semantic_scholar_handler import SemanticScholarHandler
from handlers.langchain_handler import LangChainHandler
from handlers.jina_handler import JinaHandler
from utils.text_optimizer import TextOptimizer


class PaperProcessor:
    """Service class for processing academic papers."""
    
    def __init__(self):
        self.langchain_handler = LangChainHandler()
        # Enhanced chat_threads structure with per-user LLM settings
        self.chat_threads = {}  # {user_id: {thread_id: str, current_pdf: str, llm_provider: str, llm_model: str}}
        self.default_llm_provider = self.langchain_handler.available_providers[0]
        self.default_model = self.langchain_handler.get_default_model(self.default_llm_provider)
        
        self.lang_maps = {
            'ja': 'Japanese',
            'en': 'English',
            'zh': 'Chinese',
            # add more languages here
        }
    
    def set_llm_provider(self, user_id: str, provider: str, model: str = None) -> Dict[str, str]:
        """Set the LLM provider and model for a specific user."""
        if model:
            selected_model = model
        else:
            selected_model = self.langchain_handler.get_default_model(provider)
        
        # Initialize user settings if they don't exist
        if user_id not in self.chat_threads:
            self.chat_threads[user_id] = {
                'thread_id': '',
                'current_pdf': '',
                'llm_provider': provider,
                'llm_model': selected_model
            }
        else:
            # Update existing user settings
            self.chat_threads[user_id]['llm_provider'] = provider
            self.chat_threads[user_id]['llm_model'] = selected_model
        
        return {
            "provider": provider,
            "model": selected_model,
            "message": f"✅ Set to {provider} {selected_model}."
        }
    
    def get_user_llm_settings(self, user_id: str) -> Tuple[str, str]:
        """Get LLM provider and model for a specific user."""
        if user_id in self.chat_threads:
            provider = self.chat_threads[user_id].get('llm_provider', self.default_llm_provider)
            model = self.chat_threads[user_id].get('llm_model', self.default_model)
        else:
            provider = self.default_llm_provider
            model = self.default_model
        return provider, model
    
    def get_available_models(self, provider: str = None, user_id: str = None) -> Dict[str, Any]:
        """Get available models for a provider."""
        if provider is None:
            if user_id:
                provider, _ = self.get_user_llm_settings(user_id)
            else:
                provider = self.default_llm_provider
            
        available_models = self.langchain_handler.list_available_models(provider)
        default_model = self.langchain_handler.get_default_model(provider)
        
        current_model = None
        if user_id:
            _, current_model = self.get_user_llm_settings(user_id)
        
        return {
            "provider": provider,
            "available_models": available_models,
            "default_model": default_model,
            "current_model": current_model if provider == (self.get_user_llm_settings(user_id)[0] if user_id else self.default_llm_provider) else None
        }
    
    def parse_request(self, text: str, files: Optional[list] = None) -> Tuple[str, str, Optional[Dict], str]:
        """Parse the request text and extract query, PDF URL, file info, and language."""
        # Find all URLs in the query
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        urls = re.findall(url_pattern, text)
        pdf_url = urls[0] if urls else ""  # Take the first URL found, or "" if no URLs
        
        # Remove all URLs from the query (and clean up extra whitespace)
        query = re.sub(url_pattern, '', text).strip()
        query = ' '.join(query.split())
        
        # Check for file uploads
        pdf_file = None
        if files:
            # Look for PDF files in the uploads
            for file_info in files:
                if file_info.get('mimetype') == 'application/pdf' or file_info.get('name', '').lower().endswith('.pdf'):
                    pdf_file = file_info
                    break
        
        language_code = detect(query) if query else 'en'
        language = self.lang_maps.get(language_code, 'English')
        return query, pdf_url, pdf_file, language
    
    def start_new_conversation(self, user_id: str, pdf_url: str = "", pdf_file_id: str = "") -> str:
        """Start a new conversation thread for a user."""
        thread_id = user_id + (pdf_url or pdf_file_id or "")
        
        # Preserve existing LLM settings or use defaults
        existing_provider = self.default_llm_provider
        existing_model = self.default_model
        if user_id in self.chat_threads:
            existing_provider = self.chat_threads[user_id].get('llm_provider', self.default_llm_provider)
            existing_model = self.chat_threads[user_id].get('llm_model', self.default_model)
        
        self.chat_threads[user_id] = {
            'thread_id': thread_id, 
            'current_pdf': pdf_file_id if pdf_file_id else pdf_url,
            'llm_provider': existing_provider,
            'llm_model': existing_model
        }
        return thread_id
    
    def get_or_create_thread(self, user_id: str, pdf_url: str = "", pdf_file_id: str = "", force_new: bool = False) -> Tuple[str, bool]:
        """Get existing thread or create new one. Returns (thread_id, is_new_thread)."""
        current_pdf = pdf_file_id if pdf_file_id else pdf_url
        prev_pdf = self.chat_threads.get(user_id, {}).get('current_pdf', '')
        
        is_new_paper = current_pdf != '' and current_pdf != prev_pdf
        is_new_thread = force_new or user_id not in self.chat_threads or is_new_paper
        
        if is_new_thread:
            thread_id = self.start_new_conversation(user_id, pdf_url, pdf_file_id)
            return thread_id, True
        else:
            thread_id = self.chat_threads[user_id]['thread_id']
            return thread_id, False
    
    async def process_paper(self, query: str, pdf_url: str = "", pdf_file_content: bytes = None, 
                           pdf_filename: str = "", user_id: str = "", force_new: bool = False, 
                           progress_callback = None, slack_file_info = None, slack_client = None, 
                           bot_token: str = "") -> Dict[str, Any]:
        """
        Process a paper and return analysis results.
        
        Returns a dictionary with:
        - thread_id: conversation thread ID
        - is_new_paper: whether this is a new paper analysis
        - summary: paper summary (if new paper)
        - related_papers: related papers analysis (if new paper)
        - response: continuation response (if existing conversation)
        - error: error message if any
        """
        try:
            # Handle Slack file download if needed
            if slack_file_info and slack_client and bot_token and not pdf_file_content:
                pdf_file_content = await self.download_slack_file(slack_file_info, slack_client, bot_token)
                if not pdf_filename:
                    pdf_filename = slack_file_info.get('name', 'uploaded.pdf')
            
            # Determine if we have PDF content
            has_pdf_url = pdf_url != ''
            has_pdf_file = pdf_file_content is not None
            
            if not has_pdf_url and not has_pdf_file and not query:
                return {"error": "No PDF file, URL, or query provided"}
            
            # Get or create conversation thread
            pdf_file_id = pdf_filename if has_pdf_file else ""
            thread_id, is_new_paper = self.get_or_create_thread(
                user_id, pdf_url, pdf_file_id, force_new
            )
            
            # Detect language
            language_code = detect(query) if query else 'en'
            language = self.lang_maps.get(language_code, 'English')
            
            result = {
                "thread_id": thread_id,
                "is_new_paper": is_new_paper,
                "language": language
            }
            
            if is_new_paper and (has_pdf_url or has_pdf_file):
                # Process new paper
                paper_analysis = await self._analyze_new_paper(
                    query, pdf_url, pdf_file_content, pdf_filename, thread_id, language, user_id, progress_callback
                )
                result.update(paper_analysis)
            else:
                # Continue existing conversation using user's LLM settings
                provider, model = self.get_user_llm_settings(user_id)
                model_info = f"{provider}" + (f" - {model}" if model else "")
                
                # Set the user's preferred LLM for this call
                self.langchain_handler.set_model(provider, model)
                response = self.langchain_handler.call(query, thread_id)
                result["response"] = response
                result["model_info"] = model_info
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _analyze_new_paper(self, query: str, pdf_url: str, pdf_file_content: bytes, 
                                pdf_filename: str, thread_id: str, language: str, user_id: str = "", 
                                progress_callback = None) -> Dict[str, Any]:
        """Analyze a new paper and return summary and related papers."""
        has_pdf_url = pdf_url != ''
        has_pdf_file = pdf_file_content is not None
        
        # Step 1: Fetch the text using JINA API
        if progress_callback:
            if has_pdf_file:
                await progress_callback("📁 [1/5] Processing the uploaded PDF file...")
            elif has_pdf_url:
                await progress_callback("🌐 [1/5] Fetching the paper...")
        
        jina_handler = JinaHandler()
        if has_pdf_file:
            text = jina_handler.fetch_pdf_file(pdf_file_content)
        elif has_pdf_url:
            text = jina_handler.fetch_url(pdf_url)
        else:
            raise Exception("No PDF file or URL provided")
        
        # Step 2: Get paper metadata and related papers from Semantic Scholar
        if progress_callback:
            await progress_callback("🌐 [2/5] Searching for related papers...")
        
        paper_meta = None
        related_papers_text = ""
        try:
            semantic_scholar = SemanticScholarHandler()
            if has_pdf_url:
                paper_meta = semantic_scholar.get_paper(pdf_url)
                related_papers = semantic_scholar.get_recommendations(paper_meta['paperId'])
                related_papers_text = SemanticScholarHandler.parse_related_papers_simple(related_papers)
            elif has_pdf_file:
                # Get first # title from the markdown text
                title_match = re.search(r'^#+\s*(.*?)$', text, re.MULTILINE)
                if title_match:
                    title = title_match.group(1)
                    paper_meta = semantic_scholar.search_paper(title)
                    related_papers = semantic_scholar.get_recommendations(paper_meta['paperId'])
                    related_papers_text = SemanticScholarHandler.parse_related_papers_simple(related_papers)
        except Exception as e:
            print(f"Warning: Could not fetch related papers from Semantic Scholar: {e}")
            if progress_callback:
                await progress_callback(f"⚠️ Warning: Could not fetch related papers from Semantic Scholar: {e}")
        
        # Step 3: Optimize the text
        if progress_callback:
            await progress_callback("💰 [3/5] Optimizing the text...")
        
        text_optimizer = TextOptimizer()
        optimized_result = text_optimizer.optimize_markdown(text, token_limit=4000)
        text_optimizer.display_optimization_results(optimized_result)
        
        # Add paper metadata if available
        if paper_meta:
            paper_meta_text = f"Title: {paper_meta['title']}\nAuthors: {', '.join(author['name'] for author in paper_meta['authors'])}"
            context = f"{paper_meta_text}\n\n{optimized_result['text']}"
        else:
            # For uploaded files without metadata
            filename = pdf_filename if pdf_filename else 'Unknown Title'
            paper_meta_text = f"Document: {filename}"
            context = f"{paper_meta_text}\n\n{optimized_result['text']}"
        
        # Step 4: Generate summary using user's LLM settings
        provider, model = self.get_user_llm_settings(user_id) if user_id else (self.default_llm_provider, self.default_model)
        model_info = f"{provider}" + (f" - {model}" if model else "")
        
        if progress_callback:
            await progress_callback(f"🤖 [4/5] Generating AI Summary (with: {model_info})...")
        
        # Set the user's preferred LLM for this call
        self.langchain_handler.set_model(provider, model)
        summary = self.langchain_handler.summarize_paper(query, thread_id=thread_id, context=context, language=language)
        
        # Step 5: Rank related papers if available
        if progress_callback:
            await progress_callback(f"🤖 [5/5] Ranking Related Papers (with: {model_info})...")
        
        ranked_papers = ""
        if paper_meta and related_papers_text:
            paper_meta_full = f"{paper_meta_text}\nAbstract: {paper_meta['abstract']}"
            ranked_papers = self.langchain_handler.rank_related_papers(
                thread_id=thread_id, main_paper=paper_meta_full, 
                related_papers=related_papers_text, language=language
            )
        
        return {
            "summary": summary,
            "related_papers": ranked_papers,
            "paper_meta": paper_meta,
            "model_info": model_info,
            "optimization_stats": optimized_result
        }
    
    def markdown_to_slack(self, text: str) -> str:
        """Convert markdown to Slack-compatible format."""
        converter = SlackMarkdownConverter()
        return converter.convert(text)
    
    async def download_slack_file(self, file_info, slack_client, bot_token: str):
        """
        Download file content from Slack
        
        Args:
            file_info: Slack file information dict
            slack_client: Async Slack app client for API calls
            bot_token: Slack bot token for authorization
            
        Returns:
            bytes: File content as bytes
        """
        try:
            # Get file info with download URL
            file_response = await slack_client.files_info(file=file_info['id'])
            file_data = file_response['file']
            
            # Download the file content
            headers = {'Authorization': f'Bearer {bot_token}'}
            import requests
            response = requests.get(file_data['url_private_download'], headers=headers)
            response.raise_for_status()
            
            return response.content
        except Exception as e:
            raise Exception(f"Failed to download file from Slack: {str(e)}")
