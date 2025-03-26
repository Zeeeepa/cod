# Webhook Setup Guide

This guide will help you set up webhooks for your Codegen app deployed on Modal.

## Prerequisites

Before setting up webhooks, make sure you have:

1. Deployed your app to Modal using `modal deploy app.py`
2. Set up the required environment variables in your `.env` file:
   ```
   GITHUB_WEBHOOK_SECRET=your_github_webhook_secret
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_SIGNING_SECRET=your_slack_signing_secret
   SLACK_NOTIFICATION_CHANNEL=your_channel_id
   GITHUB_TOKEN=github_pat_your_token
   ANTHROPIC_API_KEY=your_anthropic_key
   ```

## 1. Slack Webhook Setup

1. Go to your [Slack App's settings page](https://api.slack.com/apps)
2. Select your app
3. Navigate to "Event Subscriptions" in the sidebar
4. Toggle "Enable Events" to On
5. In the "Request URL" field, enter:
   ```
   https://your-modal-app-url/slack/events
   ```
   (Replace `your-modal-app-url` with your actual Modal app URL)
6. Wait for Slack to verify the URL (it will send a challenge that your app should respond to)
7. Under "Subscribe to bot events", add the following events:
   - `app_mention` (to handle mentions)
   - `message.im` (to handle direct messages)
8. Click "Save Changes"
9. Go to "OAuth & Permissions" and ensure your bot has the required scopes:
   - `app_mentions:read`
   - `chat:write`
   - `im:history` (for direct messages)
   - Any other permissions needed for your app

## 2. GitHub Webhook Setup

1. Go to your GitHub repository
2. Navigate to "Settings" > "Webhooks"
3. Click "Add webhook"
4. In the "Payload URL" field, enter:
   ```
   https://your-modal-app-url/github/events
   ```
   (Replace `your-modal-app-url` with your actual Modal app URL)
5. Set "Content type" to `application/json`
6. Enter your webhook secret (same as `GITHUB_WEBHOOK_SECRET` in your .env file)
7. Under "Which events would you like to trigger this webhook?", select:
   - "Let me select individual events" and choose:
     - Pull requests (for PR events)
     - Any other events you need
8. Click "Add webhook"

## Troubleshooting

If webhooks aren't working:

1. Check Modal logs: `modal app logs codegen-test`
2. Verify webhook deliveries in each platform's settings
3. Ensure your .env file has all required secrets
4. Check that your app has the necessary permissions

### Common Issues

#### Slack URL Verification Fails

If Slack can't verify your URL, make sure:
- Your app is properly handling the `url_verification` event type
- Your app is returning the `challenge` parameter in the response

#### GitHub Webhook Signature Verification Fails

If GitHub webhook signature verification fails:
- Ensure your `GITHUB_WEBHOOK_SECRET` matches the secret you set in GitHub
- Check that your app is properly verifying the signature

#### Webhook Events Not Being Processed

If events are being received but not processed:
- Check that you've registered the correct event handlers
- Verify that the event types match what your handlers expect
- Look for any errors in the Modal logs

## Testing Your Webhooks

After setting up your webhooks, you can test them by:

1. **For Slack**: Mention your bot in a channel or send it a direct message
2. **For GitHub**: Create a PR or add a label to an existing PR

You should see logs in your Modal deployment showing the received events.