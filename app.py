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

chat_threads = {}   # {user_id: {thread_id: thread_id, pdf_url: pdf_url}}

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
    
    pdf_file = None                                         # TODO: implement this
    language_code = detect(query) if query else 'en'
    language = lang_maps.get(language_code, 'English')
    return query, pdf_url, pdf_file, language


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
        is_new_paper = pdf_url != '' and pdf_url != chat_threads.get(user_id, {}).get('pdf_url', '')
        if '/new' in query or user_id not in chat_threads:
            is_new_paper = True
            thread_id = user_id + pdf_url
            chat_threads[user_id] = {'thread_id': thread_id, 'pdf_url': pdf_url}
            print(f"Starting new thread {thread_id}...")
            say("🆕 _Starting a new conversation..._ \nℹ️ _(Type '/new' after mentioning me to start a new conversation)_")
        else:
            thread_id = chat_threads[user_id]['thread_id']  # use the existing thread id (continue the conversation)
            print(f"Continuing thread {thread_id}...")
            say("➡️ _Continuing the conversation..._ \nℹ️ _(Type '/new' after mentioning me to start a new conversation)_")
        
        if is_new_paper:
            say("⏳ Processing the paper...")
            # 1. Get the paper meta and related papers from Semantic Scholar
            try:
                semantic_scholar = SemanticScholarHandler()
                paper_meta = semantic_scholar.get_paper(pdf_url)
                related_papers = semantic_scholar.get_recommendations(paper_meta['paperId'])
                related_papers_text = parse_related_papers(related_papers)
                related_papers_text = markdown_to_slack(related_papers_text)
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 2. Fetch the text from the url using JINA API
            try:
                jina_handler = JinaHandler()
                text = jina_handler.fetch_url(pdf_url)
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 3. Optimize the text using TextOptimizer
            try:
                text_optimizer = TextOptimizer()
                optimized_result = text_optimizer.optimize_markdown(text, token_limit=4000)
                text_optimizer.display_optimization_results(optimized_result)
                paper_meta_text = f"Title: {paper_meta['title']}\nAuthors: {', '.join(author['name'] for author in paper_meta['authors'])}"
                context = optimized_result["text"]
                context = f"{paper_meta_text}\n\n{context}"
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 4. Summarize the paper using LangChain
            try:
                summary = langchain_handler.summarize_paper(query, thread_id=thread_id, context=context, language=language)
                summary = "# 📄 Summary \n\n────────── \n\n" + summary + "\n\n────────── \n\n"
                summary = markdown_to_slack(summary)
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 5. Digest and rank the related papers using LangChain
            try:
                paper_meta_text = f"{paper_meta_text}\nAbstract: {paper_meta['abstract']}"
                related_papers_text = langchain_handler.rank_related_papers(thread_id=thread_id, main_paper=paper_meta_text, related_papers=related_papers_text, language=language)
                related_papers_text = "# 📚 Related Papers \n\n────────── \n\n" + related_papers_text + "\n\n────────── \n\n"
                related_papers_text = markdown_to_slack(related_papers_text)
            except Exception as e:
                say(f"❌ Error: {e}")
                return
            
            # 6. Output the summary and related papers
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
