# ScholarBot

**🌐 Language | 言語:** **English** | [日本語](README_JP.md)

> **Note:** This English version contains the most accurate and up-to-date information.

A powerful AI bot for analyzing academic papers, extracting insights, and discovering related research using advanced language models and PDF processing capabilities. Built with FastAPI, LangChain, OpenAI, and Slack Bot integration.

## 🚀 Features

- **PDF Processing**: Extract and analyze text from PDF files and URLs
- **AI-Powered Summarization**: Generate comprehensive paper summaries using state-of-the-art LLMs (GPT-4)
- **Related Paper Discovery**: Find semantically similar research papers using Semantic Scholar API
- **FastAPI Web Server**: Modern async web API with automatic documentation
- **Slack Integration**: Webhook-based integration with Slack for team collaboration  
- **ngrok Support**: Easy public URL exposure for development and testing
- **Multi-language Support**: Automatic language detection and response in user's language
- **Memory-Aware Conversations**: Context-aware follow-up questions and discussions

## 🛠️ Setup

### Prerequisites

1. **Python Environment**
   ```bash
   conda create -n scholarbot python=3.12
   conda activate scholarbot
   pip install -r requirements.txt
   ```

2. **API Keys Required**
   
   **Essential Keys (Required for basic functionality):**
   - **Jina AI API Key**: Get from [Jina AI](https://jina.ai/) - Required for PDF text extraction
   - **Slack Bot Token**: Create a Slack app and get bot token - Required for Slack integration  
   - **Slack Signing Secret**: Get from your Slack app settings - Required for webhook verification
   
    **LLM Provider Keys (Choose at least one):**
    - **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys) - For GPT-4 models
    - **Google Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/) - For Gemini models
    - **Google Cloud Credentials**: For Vertex AI access - Download service account JSON from [Google Cloud Console](https://console.cloud.google.com/)
    - **Anthropic API Key**: Get from [Anthropic Console](https://console.anthropic.com/) - For Claude models
   
   **Optional Keys:**
   - **LangChain API Key**: Get from [LangChain](https://smith.langchain.com/) - For conversation tracing and debugging

### Configuration

1. **Environment Variables**
   Create a `.env` file in the project root:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_SIGNING_SECRET=your-slack-signing-secret
   JINA_API_KEY=your_jina_api_key
   OPENAI_API_KEY=your_openai_api_key  # If you want to use OpenAI
   GOOGLE_API_KEY=your_gemini_api_key  # If you want to use Google Gemini API
   GOOGLE_APPLICATION_CREDENTIALS=path_to_your_vertexai_credential_json # If you want to use Google VertexAI API
   ANTHROPIC_API_KEY=your_anthropic_api_key  # If you want to use Anthropic API
   LANGCHAIN_API_KEY=your_langchain_api_key  # Optional for tracing
   ```

2. **Slack App Setup**
   - Create a new Slack app at [api.slack.com](https://api.slack.com/apps)
   - **Important**: This app uses Slack Bolt with webhook endpoints for event handling
   - Add Bot Token Scopes: `app_mentions:read`, `chat:write`, `files:read`
   - Configure Event Subscriptions:
     - Enable Events and set Request URL to your ngrok tunnel + `/slack/events`
     - Subscribe to `app_mention` events
   - Configure Interactivity:
     - Enable Interactivity and set Request URL to your ngrok tunnel + `/slack/interactions`
   - Install the app to your workspace
   - Copy the Bot User OAuth Token and Signing Secret (from Basic Information)

## 🚀 Usage

### Running the Server

**Option 1: Using the startup script (recommended)**
```bash
python start_server.py
```

**Option 2: Manual startup**
```bash
# Start the FastAPI server
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000

# In another terminal, start ngrok (optional)
ngrok http 8000
```

**Option 3: Development mode with auto-reload**
```bash
python start_server.py --reload
```

The startup script will:
- Start the FastAPI server on port 8000 with Slack Bolt webhook endpoints
- Automatically start an ngrok tunnel (unless `--no-ngrok` is specified)
- Display the public URLs for Slack webhook configuration

**Note**: Webhook mode requires ngrok (or similar) for Slack to reach your local development server.

### Using the Agent

1. **Slack Commands**
   - `@YourBot https://arxiv.org/pdf/2301.00000.pdf Summarize this paper` - Analyze and summarize any PDF paper, and automatically discover similar research
   - `@YourBot /new Now summarize this paper https://...` - Start a fresh conversation (clears previous context)
   - `@YourBot /select_llm_provider` - Choose your preferred LLM provider (ChatGPT, Google, ...)

2. **Available Endpoints** (for monitoring/debugging)
   - `GET /health` - Health check and current configuration
   - `GET /slack/status` - Slack connection status
   - `GET /docs` - FastAPI automatic documentation

3. **Supported Operations**
   - Share a PDF URL / PDF file with any question
   - Ask for paper summaries
   - Request related paper discovery
   - Follow-up questions about previously analyzed papers

### Features in Action

- **Automatic Language Detection**: The bot responds in the same language as your query
- **Context Memory**: Each user has their own conversation thread for follow-up questions
- **Rich Responses**: Well-formatted paper summaries and related paper rankings

## 📋 Development Status

- [x] PDF URL input processing
- [x] PDF file upload support (via Slack)
- [x] Text extraction from PDFs
- [x] LLM-powered paper summarization
- [x] Related paper discovery (Semantic Scholar API)
- [x] FastAPI web server with webhook integration
- [x] Slack integration with Event Subscriptions
- [x] ngrok tunnel support for development
- [x] Multi-language support and auto-detection
- [x] Memory-aware conversations with thread management
- [x] File upload support (beyond URLs)
- [x] Support different model providers
- [ ] Enhanced error handling and validation
- [ ] Change from socket mode to web api mode

## 🤝 Contributing

Please feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

