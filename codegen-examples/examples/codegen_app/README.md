# Codegen Slack Bot

This is a Slack bot application built with Codegen that can respond to mentions and direct messages.

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

4. Run the application:
   ```bash
   python fixed_app.py
   ```

## Troubleshooting Anthropic API Issues

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

## Running Without Anthropic API

If you want to run the bot without requiring the Anthropic API, you can use the simple version:

```bash
python simple_app.py
```

This version will respond to mentions and direct messages with predefined responses, without using the Anthropic API.

## Testing the Integration

You can test the Slack and Anthropic integration separately:

```bash
python run_tests.py
```

This will:
1. Send a test message to your Slack channel
2. Test the Anthropic API connection
3. Report any issues with either integration

## Exposing Your Local Server

To make your bot accessible to Slack, you need to expose your local server:

1. Install ngrok: https://ngrok.com/download
2. Run ngrok to expose your local server:
   ```bash
   ngrok http 8000
   ```
3. Copy the HTTPS URL provided by ngrok
4. Configure your Slack app's Event Subscriptions URL with: `https://your-ngrok-url/slack/events`

## Deploy to Modal

This will deploy it as a function:

```bash
modal deploy app.py
```

Then you can swap in the modal URL for Slack event subscriptions.
