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
current_llm_provider = langchain_handler.available_providers[0]

lang_maps = {
    'ja': 'Japanese',
    'en': 'English',
    'zh': 'Chinese',
    # add more languages here
}

# LLM provider selector menu block
llm_provider_menu_blocks = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Select a LLM provider and then press confirm."
        }
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "static_select",
                "placeholder": {"type": "plain_text", "text": "Select a LLM provider", "emoji": True},
                "options": [
                    {
                        "text": {"type": "plain_text", "text": provider},
                        "value": provider
                    }
                    for provider in langchain_handler.available_providers
                ],
                "initial_option": {
                    "text": {"type": "plain_text", "text": langchain_handler.available_providers[0]},
                    "value": langchain_handler.available_providers[0]
                },
                "action_id": "llm_provider_select_action"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Confirm",
                    "emoji": True
                },
                "style": "primary",
                "value": "confirm_button",
                "action_id": "llm_provider_confirm_action"
            }
        ]
    }
]


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




@app.action("llm_provider_select_action")
def handle_llm_provider_select(ack, body, say):
    global current_llm_provider
    ack()  # Acknowledge the action
    selected_value = body["actions"][0]["selected_option"]["value"]
    current_llm_provider = selected_value

@app.action("llm_provider_confirm_action")
def handle_llm_provider_confirm(ack, body, say):
    ack()  # Acknowledge the action
    global current_llm_provider
    langchain_handler.set_model(current_llm_provider)
    say(f"✅ Set to the selected LLM provider: {current_llm_provider}.")



@app.event("app_mention")
def handle_app_mention(event, say):
    print(f"Received event: {event}")
    print(f"chat_threads: {chat_threads}")
    if event and 'text' in event:
        # 0. Handle the /select_llm_provider command
        if "/select_llm_provider" in event['text']:
            say(blocks=llm_provider_menu_blocks, text="Choose a LLM provider:")
            return
        
        # 1. Parse query & check if the user has a thread id
        query, pdf_url, pdf_file, language = parse_event(event)
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
        
        # 2. Process the paper
        if is_new_paper:
            has_pdf_url = pdf_url != ''
            has_pdf_file = pdf_file is not None
            
            # 2.1 Fetch the text using JINA API (either from URL or uploaded file)
            try:
                jina_handler = JinaHandler()
                if has_pdf_file:
                    # Handle uploaded file
                    say("📁 [1/5] Processing the uploaded PDF file...")
                    pdf_content = download_slack_file(pdf_file, app.client)
                    text = jina_handler.fetch_pdf_file(pdf_content)
                elif has_pdf_url:
                    # Handle URL
                    say("🌐 [1/5] Fetching the paper...")
                    text = jina_handler.fetch_url(pdf_url)
                else:
                    say("❌ Error: No PDF file or URL provided")
                    return
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 2.2 Get the paper meta and related papers from Semantic Scholar (only for URLs)            
            paper_meta = None
            related_papers_text = ""
            try:
                say("🌐 [2/5] Searching for related papers...")
                if has_pdf_url:
                    semantic_scholar = SemanticScholarHandler()
                    paper_meta = semantic_scholar.get_paper(pdf_url)
                    related_papers = semantic_scholar.get_recommendations(paper_meta['paperId'])
                    related_papers_text = SemanticScholarHandler.parse_related_papers_simple(related_papers)
                    related_papers_text = markdown_to_slack(related_papers_text)
                elif has_pdf_file:
                    # get first # title from the markdown text
                    title = re.search(r'^#+\s*(.*?)$', text, re.MULTILINE).group(1)
                    semantic_scholar = SemanticScholarHandler()
                    paper_meta = semantic_scholar.search_paper(title)
                    related_papers = semantic_scholar.get_recommendations(paper_meta['paperId'])
                    related_papers_text = SemanticScholarHandler.parse_related_papers_simple(related_papers)
                    related_papers_text = markdown_to_slack(related_papers_text)
                else:
                    say("❌ Error: No PDF file or URL provided")
                    return
            except Exception as e:
                say(f"⚠️ Warning: Could not fetch related papers from Semantic Scholar: {e}")
                # Continue processing without related papers
            
            # 2.3 Optimize the text using TextOptimizer
            paper_meta_text = ""
            context = ""
            try:
                say("💰 [3/5] Optimizing the text...")
                text_optimizer = TextOptimizer()
                optimized_result = text_optimizer.optimize_markdown(text, token_limit=4000)
                text_optimizer.display_optimization_results(optimized_result)
                
                # Add paper metadata if available
                if paper_meta:
                    paper_meta_text = f"Title: {paper_meta['title']}\nAuthors: {', '.join(author['name'] for author in paper_meta['authors'])}"
                    context = f"{paper_meta_text}\n\n{optimized_result['text']}"
                else:
                    # For uploaded files without metadata
                    filename = pdf_file.get('name', 'Uploaded PDF') if has_pdf_file else 'Unknown Title'
                    paper_meta_text = f"Document: {filename}"
                    context = f"{paper_meta_text}\n\n{optimized_result['text']}"
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 2.4 Summarize the paper using LangChain
            try:
                say(f"🤖 [4/5] Generating AI Summary (with LLM provider: {current_llm_provider})...")
                summary = langchain_handler.summarize_paper(query, thread_id=thread_id, context=context, language=language)
                summary = "# 📄 Summary \n\n────────── \n\n" + summary + "\n\n────────── \n\n"
                summary = markdown_to_slack(summary)
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 2.5 Digest and rank the related papers using LangChain (only if we have related papers)
            try:
                say(f"🤖 [5/5] Ranking Related Papers (with LLM provider: {current_llm_provider})...")
                if paper_meta:
                    paper_meta_full = f"{paper_meta_text}\nAbstract: {paper_meta['abstract']}"
                else:
                    paper_meta_full = context
                related_papers_text = langchain_handler.rank_related_papers(thread_id=thread_id, main_paper=paper_meta_full, related_papers=related_papers_text, language=language)
                related_papers_text = "# 📚 Related Papers \n\n────────── \n\n" + related_papers_text + "\n\n────────── \n\n"
                related_papers_text = markdown_to_slack(related_papers_text)
            except Exception as e:
                say(f"⚠️ Warning: Could not process related papers: {e}")
            
            # 2.6 Output the summary and related papers
            say("✅ Analysis Complete!")
            summary = summary if summary else "☹️ No summary available."
            related_papers_text = related_papers_text if related_papers_text else "☹️ No related papers available."
            say(summary)
            say(related_papers_text)
            
        # 3. Continue the conversation
        else:
            say(f"🤖 Continuing the conversation (with LLM provider: {current_llm_provider})...")
            response = langchain_handler.call(query, thread_id)
            response = markdown_to_slack(response)
            if response and response.strip():
                say(response)
        
    else:
        say("Cannot get the message content.")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
