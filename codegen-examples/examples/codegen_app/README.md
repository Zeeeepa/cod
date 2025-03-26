# Codegen App

Simple example of running a codegen app.

## Run Locally

Spin up the server:

```
codegen serve
```

Spin up ngrok

```
ngrok http 8000
```

Go to Slack [app settings](https://api.slack.com/apps/A08CR9HUJ3W/event-subscriptions) and set the URL for event subscriptions

```
{ngrok_url}/slack/events
```

## Deploy to Modal

This will deploy it as a function:

```bash
chmod +x deploy_modal.sh
./deploy_modal.sh
```

Then you can swap in the modal URL for slack etc.

## Troubleshooting

If you encounter the "bad argument type for built-in operation" error, make sure you're using the deployment script which properly sets up the environment.

The most common issues are:
1. Missing environment variables
2. Incorrect Modal configuration
3. Import errors for the codegen package

### Environment Variables

The app uses the following environment variables:

- `GITHUB_TOKEN` - GitHub personal access token
- `SLACK_BOT_TOKEN` - Slack bot token
- `SLACK_SIGNING_SECRET` - Slack signing secret
- `SLACK_NOTIFICATION_CHANNEL` - Slack channel ID for notifications
- `ANTHROPIC_API_KEY` (optional) - Anthropic API key for Claude models
- `OPENAI_API_KEY` (optional) - OpenAI API key for GPT models
