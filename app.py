import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests
from dotenv import load_dotenv
from langdetect import detect
from markdown_to_mrkdwn import SlackMarkdownConverter
from urllib.parse import urlparse, unquote
from handlers.semantic_scholar_handler import SemanticScholarHandler
from handlers.langchain_handler import LangChainHandler
from handlers.jina_handler import JinaHandler
from utils.text_optimizer import TextOptimizer



load_dotenv()
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
bot_user_id = app.client.auth_test()["user_id"]
langchain_handler = LangChainHandler()

chat_threads = {}   # {user_id: {thread_id: thread_id, current_pdf: pdf_url or pdf_file_id}}

lang_maps = {
    'ja': 'Japanese',
    'en': 'English',
    'zh': 'Chinese',
    # add more languages here
}




def parse_event(event):
    query_raw = event['text'].replace(f"<@{bot_user_id}>", "").strip()  # remove the mention part    
    
    # Find all URLs in the query
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
    urls = re.findall(url_pattern, query_raw)
    pdf_url = urls[0] if urls else ""  # Take the first URL found, or "" if no URLs
    
    # Remove all URLs from the query (and clean up extra whitespace)
    query = re.sub(url_pattern, '', query_raw).strip()
    query = ' '.join(query.split())
    
    # Check for file uploads
    pdf_file = None
    if 'files' in event and event['files']:
        # Look for PDF files in the uploads
        for file_info in event['files']:
            if file_info.get('mimetype') == 'application/pdf' or file_info.get('name', '').lower().endswith('.pdf'):
                pdf_file = file_info
                break
    
    language_code = detect(query) if query else 'en'
    language = lang_maps.get(language_code, 'English')
    return query, pdf_url, pdf_file, language


def download_slack_file(file_info, app_client):
    """
    Download file content from Slack
    
    Args:
        file_info: Slack file information dict
        app_client: Slack app client for API calls
        
    Returns:
        bytes: File content as bytes
    """
    try:
        # Get file info with download URL
        file_response = app_client.files_info(file=file_info['id'])
        file_data = file_response['file']
        
        # Download the file content
        headers = {'Authorization': f'Bearer {os.environ.get("SLACK_BOT_TOKEN")}'}
        response = requests.get(file_data['url_private_download'], headers=headers)
        response.raise_for_status()
        
        return response.content
    except Exception as e:
        raise Exception(f"Failed to download file from Slack: {str(e)}")


def markdown_to_slack(text):
    converter = SlackMarkdownConverter()
    mrkdwn_text = converter.convert(text)
    return mrkdwn_text


def parse_related_papers(related_papers):
    related_papers_text = "────────── \n\n# 📚 Related Papers \n\n────────── \n\n"
    for paper in related_papers:
        related_papers_text += f"## [{paper['title']}]({paper['url']}) \n"
        related_papers_text += f"- Authors: {', '.join(author['name'] for author in paper['authors'])}\n"
        related_papers_text += f"- Year: {paper['year']}\n"
        related_papers_text += f"- Abstract: {paper['abstract']}\n"
        related_papers_text += "\n────────── \n\n"
    return related_papers_text



@app.event("app_mention")
def handle_app_mention(event, say):
    print(event)
    if event and 'text' in event:
        query, pdf_url, pdf_file, language = parse_event(event)
        
        # 0. Check if the user has a thread id
        user_id = event['user']
        prev_pdf = chat_threads.get(user_id, {}).get('current_pdf', '')
        is_new_paper = pdf_url != '' and pdf_url != prev_pdf or pdf_file is not None and pdf_file['id'] != prev_pdf
        if '/new' in query or user_id not in chat_threads:
            is_new_paper = True
            thread_id = user_id + pdf_url
            chat_threads[user_id] = {'thread_id': thread_id, 'current_pdf': pdf_file['id'] if pdf_file else pdf_url}
            print(f"Starting new thread {thread_id}...")
            say("🆕 _Starting a new conversation..._ \nℹ️ _(Type '/new' after mentioning me to start a new conversation)_")
        else:
            thread_id = chat_threads[user_id]['thread_id']  # use the existing thread id (continue the conversation)
            print(f"Continuing thread {thread_id}...")
            say("➡️ _Continuing the conversation..._ \nℹ️ _(Type '/new' after mentioning me to start a new conversation)_")
        
        if is_new_paper:
            say("⏳ Processing the paper...")
            
            # Define helper variables for readability
            has_pdf_url = pdf_url != ''
            has_pdf_file = pdf_file is not None
            
            # 1. Fetch the text using JINA API (either from URL or uploaded file)
            try:
                jina_handler = JinaHandler()
                if has_pdf_file:
                    # Handle uploaded file
                    say("📥 Processing uploaded PDF file...")
                    pdf_content = download_slack_file(pdf_file, app.client)
                    text = jina_handler.fetch_pdf_file(pdf_content)
                elif has_pdf_url:
                    # Handle URL
                    text = jina_handler.fetch_url(pdf_url)
                else:
                    say("❌ Error: No PDF file or URL provided")
                    return
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 2. Get the paper meta and related papers from Semantic Scholar (only for URLs)xt            paper_meta = None
            related_papers_text = ""
            try:
                if has_pdf_url:
                    semantic_scholar = SemanticScholarHandler()
                    paper_meta = semantic_scholar.get_paper(pdf_url)
                    related_papers = semantic_scholar.get_recommendations(paper_meta['paperId'])
                    related_papers_text = parse_related_papers(related_papers)
                    related_papers_text = markdown_to_slack(related_papers_text)
                elif has_pdf_file:
                    # get first # title from the markdown text
                    title = re.search(r'^#+\s*(.*?)$', text, re.MULTILINE).group(1)
                    semantic_scholar = SemanticScholarHandler()
                    paper_meta = semantic_scholar.search_paper(title)
                    related_papers = semantic_scholar.get_recommendations(paper_meta['paperId'])
                    related_papers_text = parse_related_papers(related_papers)
                    related_papers_text = markdown_to_slack(related_papers_text)
                else:
                    say("❌ Error: No PDF file or URL provided")
                    return
            except Exception as e:
                say(f"⚠️ Warning: Could not fetch related papers from Semantic Scholar: {e}")
                # Continue processing without related papers
            
            # 3. Optimize the text using TextOptimizer
            try:
                text_optimizer = TextOptimizer()
                optimized_result = text_optimizer.optimize_markdown(text, token_limit=4000)
                text_optimizer.display_optimization_results(optimized_result)
                
                # Add paper metadata if available
                if paper_meta:
                    paper_meta_text = f"Title: {paper_meta['title']}\nAuthors: {', '.join(author['name'] for author in paper_meta['authors'])}"
                    context = f"{paper_meta_text}\n\n{optimized_result['text']}"
                else:
                    # For uploaded files without metadata
                    filename = pdf_file.get('name', 'Uploaded PDF') if has_pdf_file else 'PDF Document'
                    paper_meta_text = f"Document: {filename}"
                    context = f"{paper_meta_text}\n\n{optimized_result['text']}"
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 4. Summarize the paper using LangChain
            try:
                say("🤖 Generating AI Summary...")
                summary = langchain_handler.summarize_paper(query, thread_id=thread_id, context=context, language=language)
                summary = "# 📄 Summary \n\n────────── \n\n" + summary + "\n\n────────── \n\n"
                summary = markdown_to_slack(summary)
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 5. Digest and rank the related papers using LangChain (only if we have related papers)
            if related_papers_text and paper_meta:
                try:
                    say("🤖 Ranking Related Papers...")
                    paper_meta_full = f"{paper_meta_text}\nAbstract: {paper_meta['abstract']}"
                    related_papers_text = langchain_handler.rank_related_papers(thread_id=thread_id, main_paper=paper_meta_full, related_papers=related_papers_text, language=language)
                    related_papers_text = "# 📚 Related Papers \n\n────────── \n\n" + related_papers_text + "\n\n────────── \n\n"
                    related_papers_text = markdown_to_slack(related_papers_text)
                except Exception as e:
                    say(f"⚠️ Warning: Could not process related papers: {e}")
                    related_papers_text = ""
            
            # 6. Output the summary and related papers
            say("✅ Analysis Complete!")
            say(summary)
            say(related_papers_text)
        else:
            # 1. Continue the conversation
            response = langchain_handler.call(query, thread_id)
            response = markdown_to_slack(response)
            say(response)
        
    else:
        say("Cannot get the message content.")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
