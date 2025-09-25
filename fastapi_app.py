"""
FastAPI application for the Scholar Bot with Slack Bolt integration.
Combines FastAPI REST API with Slack Bolt for event handling.
"""
import os
import asyncio
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from services.paper_processor import PaperProcessor

load_dotenv()

# Initialize Slack Bolt async app
slack_app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize FastAPI app
app = FastAPI(
    title="Scholar Bot API", 
    description="Academic paper analysis bot with AI-powered summarization and Slack Bolt integration",
    version="2.0.0"
)

# Initialize the paper processor
paper_processor = PaperProcessor()

# Initialize Slack request handler for FastAPI integration
slack_handler = AsyncSlackRequestHandler(slack_app)

# Get bot user ID for mentions (will be set during startup)
bot_user_id = None

async def initialize_bot_user_id():
    """Initialize bot user ID asynchronously."""
    global bot_user_id
    if bot_user_id is None:
        auth_test = await slack_app.client.auth_test()
        bot_user_id = auth_test["user_id"]
    return bot_user_id

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN is required")
if not SLACK_SIGNING_SECRET:
    raise ValueError("SLACK_SIGNING_SECRET is required for webhook verification")


# Language mapping for detection
lang_maps = {
    'ja': 'Japanese',
    'en': 'English', 
    'zh': 'Chinese',
    # add more languages here
}

async def download_slack_file(file_info, app_client):
    """
    Download file content from Slack
    
    Args:
        file_info: Slack file information dict
        app_client: Async Slack app client for API calls
        
    Returns:
        bytes: File content as bytes
    """
    try:
        # Get file info with download URL
        file_response = await app_client.files_info(file=file_info['id'])
        file_data = file_response['file']
        
        # Download the file content
        headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        import requests
        response = requests.get(file_data['url_private_download'], headers=headers)
        response.raise_for_status()
        
        return response.content
    except Exception as e:
        raise Exception(f"Failed to download file from Slack: {str(e)}")


def markdown_to_slack(text):
    """Convert markdown to Slack mrkdwn format."""
    from markdown_to_mrkdwn import SlackMarkdownConverter
    converter = SlackMarkdownConverter()
    mrkdwn_text = converter.convert(text)
    return mrkdwn_text


def generate_llm_menu_blocks(user_id: str = None):
    """Generate LLM provider and model selector menu blocks for a specific user."""
    if user_id:
        current_llm_provider, current_model = paper_processor.get_user_llm_settings(user_id)
    else:
        current_llm_provider = paper_processor.default_llm_provider
        current_model = paper_processor.default_model
    
    available_models = paper_processor.langchain_handler.list_available_models(current_llm_provider)
    default_model = paper_processor.langchain_handler.get_default_model(current_llm_provider)
    
    # Create model options with "(recommended)" label for default model
    model_options = []
    if available_models:
        for model in available_models:
            display_text = model
            if model == default_model:
                display_text = f"{model} (recommended)"
            model_options.append({
                "text": {"type": "plain_text", "text": display_text},
                "value": model
            })
    else:
        model_options = [{"text": {"type": "plain_text", "text": "No models available"}, "value": "none"}]
    
    # Determine initial model selection
    initial_model = current_model if current_model else default_model
    
    # Find the matching option text for the initial model
    initial_option = None
    if initial_model:
        for option in model_options:
            if option["value"] == initial_model:
                initial_option = option
                break
    
    # Fallback if no match found
    if not initial_option and model_options and model_options[0]["value"] != "none":
        initial_option = model_options[0]
    
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Select a LLM provider and model, then press confirm."
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
                        for provider in paper_processor.langchain_handler.available_providers
                    ],
                    "initial_option": {
                        "text": {"type": "plain_text", "text": current_llm_provider},
                        "value": current_llm_provider
                    },
                    "action_id": "llm_provider_select_action"
                },
                {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select a model", "emoji": True},
                    "options": model_options,
                    **({"initial_option": initial_option} if initial_option else {}),
                    "action_id": "llm_model_select_action"
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


# Slack Bolt Event Handlers
@slack_app.action("llm_provider_select_action")
async def handle_llm_provider_select(ack, body, say):
    """Handle LLM provider selection."""
    await ack()  # Acknowledge the action
    user_id = body["user"]["id"]
    selected_value = body["actions"][0]["selected_option"]["value"]
    
    # Set provider for this specific user
    result = paper_processor.set_llm_provider(user_id, selected_value)
    
    # Regenerate menu blocks for this user and update the message
    new_blocks = generate_llm_menu_blocks(user_id)
    
    # Update the message with new menu blocks
    await slack_app.client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        blocks=new_blocks,
        text="Choose a LLM provider and model:"
    )


@slack_app.action("llm_model_select_action")
async def handle_llm_model_select(ack, body, say):
    """Handle LLM model selection."""
    await ack()  # Acknowledge the action
    user_id = body["user"]["id"]
    selected_value = body["actions"][0]["selected_option"]["value"]
    if selected_value != "none":
        # Get current provider for this user
        current_provider, _ = paper_processor.get_user_llm_settings(user_id)
        # Set model for this specific user
        paper_processor.set_llm_provider(user_id, current_provider, selected_value)


@slack_app.action("llm_provider_confirm_action")
async def handle_llm_provider_confirm(ack, body, say):
    """Handle LLM provider confirmation."""
    await ack()  # Acknowledge the action
    user_id = body["user"]["id"]
    provider, model = paper_processor.get_user_llm_settings(user_id)
    await say(f"✅ Set to {provider} {model}.")


@slack_app.event("app_mention")
async def handle_app_mention(event, say):
    """Handle app mentions from Slack.""" 
    print(f"Received event: {event}")
    
    if event and 'text' in event:
        # Handle the /select_llm_provider command
        if "/select_llm_provider" in event['text']:
            user_id = event.get('user')
            blocks = generate_llm_menu_blocks(user_id)
            await say(blocks=blocks, text="Choose a LLM provider and model.")
            return
        
        # Parse the event and process asynchronously
        try:
            await process_paper_request_async(event, say)
        except Exception as e:
            print(f"Error handling app mention: {e}")
            await say(f"❌ Error: {str(e)}")
    else:
        await say("Cannot get the message content.")


async def process_paper_request_async(event: Dict[str, Any], say):
    """Process a paper analysis request using Slack Bolt."""
    try:
        # Extract basic event details
        user_id = event.get('user')
        text = event.get('text', '')
        files = event.get('files', [])
        
        # Remove bot mention from text
        current_bot_user_id = await initialize_bot_user_id()
        text = text.replace(f"<@{current_bot_user_id}>", "").strip()
        
        # Use the existing parse_request method (no duplication!)
        query, pdf_url, pdf_file, language = paper_processor.parse_request(text, files)
        
        # Prepare file content if needed
        pdf_file_content = None
        pdf_filename = ""
        if pdf_file:
            pdf_file_content = await download_slack_file(pdf_file, slack_app.client)
            pdf_filename = pdf_file.get('name', 'uploaded.pdf')
        
        # Determine if this should be a new conversation
        force_new = '/new' in query or user_id not in paper_processor.chat_threads
        
        # Send initial status message
        if force_new or pdf_url or pdf_file:
            await say("🆕 _Starting a new conversation..._ \nℹ️ _(Type '/new' after mentioning me to start a new conversation)_")
        else:
            await say("➡️ _Continuing the conversation..._ \nℹ️ _(Type '/new' after mentioning me to start a new conversation)_")
        
        # Create async wrapper for progress messages
        async def async_progress_callback(message):
            await say(message)
        
        # Use the existing process_paper method (no duplication!)
        result = await paper_processor.process_paper(
            query=query,
            pdf_url=pdf_url,
            pdf_file_content=pdf_file_content,
            pdf_filename=pdf_filename,
            user_id=user_id,
            force_new=force_new,
            progress_callback=async_progress_callback
        )
        
        # Handle results
        if result.get('error'):
            await say(f"❌ Error: {result['error']}")
            return
        
        if result.get('is_new_paper'):
            # Send completion message and results
            await say("✅ Analysis Complete!")
            
            if result.get('summary'):
                summary = "# 📄 Summary \n\n────────── \n\n" + result['summary'] + "\n\n────────── \n\n"
                summary = paper_processor.markdown_to_slack(summary)
                await say(summary)
            
            if result.get('related_papers'):
                related_papers = "# 📚 Related Papers \n\n────────── \n\n" + result['related_papers'] + "\n\n────────── \n\n"
                related_papers = paper_processor.markdown_to_slack(related_papers)
                await say(related_papers)
        else:
            # Continue conversation
            model_info = result.get('model_info', '')
            await say(f"🤖 Continuing the conversation (with: {model_info})...")
            
            if result.get('response'):
                response = paper_processor.markdown_to_slack(result['response'])
                await say(response)
    
    except Exception as e:
        print(f"Error processing paper request: {e}")
        await say(f"❌ Error: {str(e)}")


# Slack webhook endpoints
@app.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack events using Slack Bolt."""
    return await slack_handler.handle(request)

@app.post("/slack/interactions") 
async def slack_interactions(request: Request):
    """Handle Slack interactions using Slack Bolt."""
    return await slack_handler.handle(request)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Scholar Bot API is running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "available_providers": paper_processor.langchain_handler.available_providers,
        "current_provider": paper_processor.current_llm_provider,
        "current_model": paper_processor.current_model
    }


@app.get("/slack/status")
async def slack_status():
    """Get Slack connection status."""
    return {
        "webhook_mode_active": True,
        "bot_user_id": bot_user_id,
        "signing_secret_configured": bool(SLACK_SIGNING_SECRET),
        "bot_token_configured": bool(SLACK_BOT_TOKEN)
    }




if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI server with Slack Bolt webhook integration...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
