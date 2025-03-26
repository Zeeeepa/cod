# Webhook Setup Guide for Codegen App

This guide explains how to properly set up webhooks for your Codegen app deployed on Modal.

## Deployment

First, make sure your app is deployed on Modal:

```bash
modal deploy app.py
```

After deployment, you'll get a URL like:
```
https://your-username--codegen-test-fastapi-app.modal.run
```

## Webhook URLs

For each integration, you'll need to use a specific endpoint:

- **Slack**: `https://your-username--codegen-test-fastapi-app.modal.run/slack/events`
- **GitHub**: `https://your-username--codegen-test-fastapi-app.modal.run/github/events`
- **Linear**: `https://your-username--codegen-test-fastapi-app.modal.run/linear/events`

## Slack Webhook Setup

1. Go to your [Slack App's settings page](https://api.slack.com/apps)
2. Select your app
3. Navigate to "Event Subscriptions" in the sidebar
4. Toggle "Enable Events" to On
5. In the "Request URL" field, enter your Slack webhook URL
6. Under "Subscribe to bot events", add the following events:
   - `app_mention` (to handle mentions)
   - Any other events you need (message.channels, etc.)
7. Click "Save Changes"
8. Go to "OAuth & Permissions" and ensure your bot has the required scopes:
   - `app_mentions:read`
   - `chat:write`
   - Any other permissions needed for your app

## GitHub Webhook Setup

1. Go to your GitHub repository
2. Navigate to "Settings" > "Webhooks"
3. Click "Add webhook"
4. In the "Payload URL" field, enter your GitHub webhook URL
5. Set "Content type" to `application/json`
6. Enter your webhook secret (same as `GITHUB_WEBHOOK_SECRET` in your .env file)
7. Under "Which events would you like to trigger this webhook?", select:
   - "Let me select individual events" and choose:
     - Pull requests (for PR events)
     - Any other events you need
8. Click "Add webhook"

## Linear Webhook Setup

1. Go to your Linear workspace
2. Navigate to "Settings" > "API" > "Webhooks"
3. Click "New Webhook"
4. Enter a name for your webhook (e.g., "Codegen Integration")
5. In the "URL" field, enter your Linear webhook URL
6. Select the events you want to subscribe to:
   - Issues (created, updated, etc.)
   - Any other events you need
7. Click "Create webhook"

## Environment Variables

Make sure your `.env` file contains all the necessary secrets:

```
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_NOTIFICATION_CHANNEL=your_channel_id
GITHUB_TOKEN=github_pat_your_token
ANTHROPIC_API_KEY=your_anthropic_key
```

## Troubleshooting

If webhooks aren't working:

1. Check Modal logs: `modal app logs codegen-test`
2. Verify webhook deliveries in each platform's settings
3. Ensure your .env file has all required secrets
4. Check that your app has the necessary permissions

### Common Issues

#### Slack URL Verification

If Slack is failing to verify your URL, it's likely because your app isn't properly responding to the challenge request. The app should:

1. Receive a POST request with a JSON body containing `{"type": "url_verification", "challenge": "some-challenge-string"}`
2. Respond with a JSON body containing `{"challenge": "same-challenge-string"}`

#### GitHub Webhook Secret

If GitHub webhook deliveries are failing, check that:

1. The webhook secret in your GitHub settings matches the `GITHUB_WEBHOOK_SECRET` in your .env file
2. Your app is correctly validating the webhook signature

#### Linear Webhook

If Linear webhook deliveries are failing, check that:

1. The webhook URL is correct
2. Your app is properly handling the Linear webhook format