# Migration Guide: Socket Mode to FastAPI

This guide explains how to migrate from the original socket mode Slack bot to the new FastAPI webhook-based implementation.

## What Changed

### Architecture
- **Before**: Socket mode with persistent WebSocket connection to Slack
- **After**: FastAPI web server with webhook endpoints for Slack events

### Key Benefits
1. **Better Scalability**: Web servers scale better than persistent connections
2. **Standard HTTP**: Uses standard HTTP endpoints instead of WebSocket
3. **Public API**: Exposes RESTful API for direct usage beyond Slack
4. **Modern Framework**: FastAPI provides automatic documentation and validation
5. **Development Friendly**: ngrok integration for easy local development

## Migration Steps

### 1. Update Dependencies
The new `requirements.txt` includes FastAPI and uvicorn:
```bash
pip install -r requirements.txt
```

### 2. Update Environment Variables
Replace your `.env` file:
```bash
# Old (remove these)
SLACK_APP_TOKEN=xapp-your-slack-app-token

# New (required)
SLACK_SIGNING_SECRET=your-slack-signing-secret
NGROK_AUTHTOKEN=your_ngrok_authtoken_here

# Keep these the same
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
JINA_API_KEY=your_jina_api_key
# ... other API keys
```

#### Where to get SLACK_SIGNING_SECRET:
1. Go to your Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Select your app
3. Navigate to **"Basic Information"** in the left sidebar
4. Scroll down to **"App Credentials"** section
5. Copy the **"Signing Secret"** (click "Show" if it's hidden)
6. Add it to your `.env` file as `SLACK_SIGNING_SECRET=your-signing-secret`

**Note**: This is different from the Bot User OAuth Token. The Signing Secret is used to verify that webhook requests are actually coming from Slack.

#### Optional: NGROK_AUTHTOKEN (Recommended)
While ngrok works without authentication for basic usage, setting up an auth token provides better performance and removes rate limits:

1. **Create a free ngrok account** at [ngrok.com](https://ngrok.com/signup)
2. **Get your auth token**:
   - Go to [dashboard.ngrok.com](https://dashboard.ngrok.com/)
   - Navigate to **"Your Authtoken"** section
   - Copy the authtoken
3. **Add to your `.env` file**:
   ```bash
   NGROK_AUTHTOKEN=your_ngrok_authtoken_here
   ```

**Benefits of using NGROK_AUTHTOKEN:**
- **No connection limits** (free accounts get 1 tunnel, authenticated gets more)
- **Custom domains** (on paid plans)
- **Tunnel persistence** across restarts
- **Better performance** and reliability

### 3. Update Slack App Configuration

#### Disable Socket Mode
1. Go to your Slack app settings
2. Navigate to "Socket Mode" 
3. Disable Socket Mode

#### Enable Event Subscriptions
1. Go to "Event Subscriptions"
2. Enable Events
3. Set Request URL to: `https://your-ngrok-url.ngrok.io/slack/events`
4. Subscribe to bot events: `app_mention`

#### Enable Interactivity
1. Go to "Interactivity & Shortcuts"
2. Enable Interactivity
3. Set Request URL to: `https://your-ngrok-url.ngrok.io/slack/interactions`

### 4. Update Startup Process

#### Old Way
```bash
python app.py
```

#### New Way
```bash
# Option 1: Use the startup script (recommended)
python start_server.py

# Option 2: Manual startup
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
```

## Code Changes

### Core Logic Extraction
The paper processing logic has been extracted into a reusable service:
- `services/paper_processor.py` - Contains all the core paper analysis logic
- `fastapi_app.py` - FastAPI application with Slack webhook handlers

### Available Endpoints
The new implementation provides these endpoints:
- `GET /health` - Health check and system status
- `GET /slack/status` - Slack connection status
- `POST /slack/events` - Slack event webhook
- `POST /slack/interactions` - Slack interaction webhook

### File Structure
```
├── app.py (old - can be removed)
├── fastapi_app.py (new main application)
├── start_server.py (new startup script)
├── services/
│   ├── __init__.py
│   └── paper_processor.py
└── ... (existing handlers, utils remain the same)
```

## Testing the Migration

1. **Start the server**:
   ```bash
   python start_server.py
   ```

2. **Check health endpoint**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test Slack connection status**:
   ```bash
   curl http://localhost:8000/slack/status
   ```

4. **Test Slack integration**:
   - Update your Slack app URLs to point to the ngrok tunnel
   - Mention your bot in a Slack channel with a paper URL

## Troubleshooting

### Common Issues

1. **ngrok not found**:
   ```bash
   # Option 1: Install via pip (included in requirements.txt)
   pip install pyngrok
   
   # Option 2: Install binary from https://ngrok.com/download
   ```

2. **Slack webhook verification fails**:
   - Ensure `SLACK_SIGNING_SECRET` is correctly set
   - Check that the webhook URLs are correctly configured

3. **Bot doesn't respond**:
   - Check that Event Subscriptions are enabled
   - Verify the webhook URLs are accessible
   - Check the server logs for errors

### Rollback Plan
If you need to rollback to the old socket mode:
1. Re-enable Socket Mode in your Slack app
2. Disable Event Subscriptions and Interactivity
3. Add back `SLACK_APP_TOKEN` to your `.env`
4. Run the old app: `python app.py`

