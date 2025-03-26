# Enhanced Slack Bot for Codegen

This enhanced version of the Slack bot addresses issues with message handling and ensures the bot always responds to messages, even when the Anthropic API is unavailable or encounters errors.

## Key Features

- **Robust Event Handling**: Properly handles Slack events and ensures responses are sent
- **Fallback Responses**: Provides simple responses when Anthropic API is unavailable
- **Automatic Bot ID Detection**: Automatically detects the bot's user ID to avoid infinite loops
- **Enhanced Error Handling**: Gracefully handles errors and provides fallback responses
- **Startup Notification**: Sends a notification when the bot starts up
- **API Testing**: Tests the Anthropic API on startup and falls back to simple responses if it fails

## Setup Instructions

1. Copy the `.env.template` file to `.env`:
   ```bash
   cp .env.template .env
   ```

2. Edit the `.env` file and fill in your credentials:
   ```
   # Slack Configuration
   SLACK_SIGNING_SECRET="your_slack_signing_secret"
   SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
   SLACK_NOTIFICATION_CHANNEL="your_slack_channel_id"
   
   # GitHub Configuration
   GITHUB_TOKEN="your_github_personal_access_token"
   
   # Anthropic API Key
   ANTHROPIC_API_KEY="your_anthropic_api_key"
   ```

   **Important**: Make sure there are no quotes, angle brackets, or other special characters in your API keys. The values should be entered directly without any wrapping characters.

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the enhanced application:
   ```bash
   python enhanced_app.py
   ```

## How It Works

The enhanced app includes a dedicated `SlackEventHandler` class that provides robust handling of Slack events:

1. **Bot ID Detection**: The handler automatically detects the bot's user ID to avoid infinite loops
2. **Message Extraction**: Extracts the message content from mentions
3. **Fallback Responses**: Provides simple responses when Anthropic API is unavailable
4. **Error Handling**: Gracefully handles errors and provides fallback responses

## Troubleshooting

### Bot Not Responding to Messages

If the bot is not responding to messages, check the following:

1. **Slack Token**: Make sure your `SLACK_BOT_TOKEN` is correct
2. **Bot Permissions**: Ensure the bot has the necessary permissions in Slack
3. **Event Subscriptions**: Verify that the Event Subscriptions URL is correctly configured in Slack
4. **Bot User ID**: Check the logs to see if the bot's user ID is being correctly detected

### Anthropic API Issues

If you're experiencing issues with the Anthropic API, you can use the debugging tool:

```bash
python debug_anthropic.py
```

This will provide detailed information about any issues with your API key.

### Common Issues:

1. **Quotes in API Key**: Make sure your API key doesn't have quotes around it in the `.env` file.
   - Correct: `ANTHROPIC_API_KEY=sk-ant-api03-xxxx`
   - Incorrect: `ANTHROPIC_API_KEY="sk-ant-api03-xxxx"`

2. **Angle Brackets**: Remove any angle brackets (`<`, `>`) from your API key.
   - Correct: `ANTHROPIC_API_KEY=sk-ant-api03-xxxx`
   - Incorrect: `ANTHROPIC_API_KEY=<sk-ant-api03-xxxx>`

3. **Line Breaks**: Ensure there are no line breaks or special characters in your API key.

## Exposing Your Local Server

To make your bot accessible to Slack, you need to expose your local server:

1. Install ngrok: https://ngrok.com/download
2. Run ngrok to expose your local server:
   ```bash
   ngrok http 8000
   ```
3. Copy the HTTPS URL provided by ngrok
4. Configure your Slack app's Event Subscriptions URL with: `https://your-ngrok-url/slack/events`

## Files

- `enhanced_app.py`: The main application with improved event handling
- `slack_event_handler.py`: Dedicated module for handling Slack events
- `debug_anthropic.py`: Tool for debugging Anthropic API issues
- `test_functions.py`: Functions for testing Slack and Anthropic integration