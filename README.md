# ScholarBot

**🌐 Language | 言語:** **English** | [日本語](README_JP.md)

> **Note:** This English version contains the most accurate and up-to-date information.

A powerful AI bot for analyzing academic papers, extracting insights, and discovering related research using advanced language models and PDF processing capabilities. Built with LangChain, OpenAI, and Slack Bot integration.

## 🚀 Features

- **PDF Processing**: Extract and analyze text from PDF files and URLs
- **AI-Powered Summarization**: Generate comprehensive paper summaries using state-of-the-art LLMs (GPT-4)
- **Related Paper Discovery**: Find semantically similar research papers using Semantic Scholar API
- **Slack Integration**: Seamless integration with Slack for team collaboration
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
   - **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
   - **Jina AI API Key**: Get from [Jina AI](https://jina.ai/)
   - **Slack Bot Token**: Create a Slack app and get bot token
   - **Slack App Token**: Enable Socket Mode and get app-level token

### Configuration

1. **Environment Variables**
   Create a `.env` file in the project root:
   ```bash
   OPENAI_API_KEY=your_openai_api_key
   JINA_API_KEY=your_jina_api_key
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_APP_TOKEN=xapp-your-slack-app-token
   LANGCHAIN_API_KEY=your_langchain_api_key  # Optional for tracing
   ```

2. **Slack App Setup**
   - Create a new Slack app at [api.slack.com](https://api.slack.com/apps)
   - Enable Socket Mode
   - Add Bot Token Scopes: `app_mentions:read`, `chat:write`, `files:read`
   - Install the app to your workspace
   - Copy the Bot User OAuth Token and App-Level Token

## 🚀 Usage

### Running the Slack Bot

```bash
python app.py
```

### Using the Agent

1. **Mention the bot in Slack**
   - `@YourBot https://arxiv.org/pdf/2301.00000.pdf Summarize this paper`
   - `@YourBot Can you find related papers to the one I just shared?`
   - `@YourBot /new Let's start a new conversation`

2. **Supported Commands**
   - Share a PDF URL with any question
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
- [x] Slack integration with Socket Mode
- [x] Multi-language support and auto-detection
- [x] Memory-aware conversations with thread management
- [x] File upload support (beyond URLs)
- [ ] Enhanced error handling and validation
- [ ] Deploy to AWS/GCP
- [ ] Web interface alternative to Slack
- [ ] Batch processing of multiple papers

## 🤝 Contributing

Please feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

