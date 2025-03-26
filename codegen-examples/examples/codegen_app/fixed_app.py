import logging
import os
import json
from fastapi import FastAPI, Request, Response, HTTPException, status, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional

from codegen import CodeAgent, CodegenApp
from codegen.extensions.github.types.events.pull_request import PullRequestLabeledEvent, PullRequestOpenedEvent
from codegen.extensions.slack.types import SlackEvent
from codegen.extensions.tools.github.create_pr_comment import create_pr_comment

# Import test functions
from test_functions import run_tests

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the CodegenApp
# Replace with your own repository as needed
cg = CodegenApp(name="codegen", repo="Zeeeepa/cod")

# Add CORS middleware for local development
cg.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a root endpoint for health checks
@cg.app.get("/")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "app": "codegen-local"}

@cg.app.post("/")
async def root_slack_verification(request: Request):
    """
    Handle Slack URL verification at the root endpoint.
    This is needed because Slack is sending the verification to the root URL.
    """
    logger.info("[SLACK] Received root webhook request")

    try:
        # Get the request body
        body = await request.json()
        logger.info(f"[SLACK] Root request body type: {body.get('type', 'unknown')}")

        # Handle Slack URL verification challenge
        if body.get("type") == "url_verification":
            logger.info("[SLACK] Handling URL verification challenge at root")
            challenge = body.get("challenge")
            logger.info(f"[SLACK] Returning challenge from root: {challenge}")

            # Return the challenge as plaintext as required by Slack
            return Response(
                content=challenge,
                media_type="text/plain"
            )

        # For other types, you might want to redirect to your main handler
        # or handle them directly here
        return {"message": "Received webhook at root"}

    except Exception as e:
        logger.error(f"[SLACK] Error processing root webhook: {str(e)}")
        # Return a 200 OK response to avoid Slack retrying
        return Response(status_code=200)

@cg.app.post("/slack/events")
async def slack_webhook(request: Request):
    """
    Handle Slack webhook events, including URL verification.
    This is the endpoint that should be configured in your Slack app's Event Subscriptions.
    """
    logger.info("[SLACK] Received webhook request at /slack/events")

    try:
        # Get the request body
        body = await request.json()
        logger.info(f"[SLACK] Request body type: {body.get('type', 'unknown')}")

        # Handle Slack URL verification challenge
        if body.get("type") == "url_verification":
            logger.info("[SLACK] Handling URL verification challenge")
            challenge = body.get("challenge")
            logger.info(f"[SLACK] Returning challenge: {challenge}")

            # Return the challenge as plaintext as required by Slack
            return Response(
                content=challenge,
                media_type="text/plain"
            )

        # Process the event through the normal event handlers
        return await cg.slack.handle_webhook(request)
    except Exception as e:
        logger.error(f"[SLACK] Error processing webhook: {str(e)}")
        # Return a 200 OK response to avoid Slack retrying
        return Response(status_code=200)

@cg.app.post("/github/events")
async def github_webhook(request: Request):
    """
    Handle GitHub webhook events.
    This is the endpoint that should be configured in your GitHub repository's webhook settings.
    """
    logger.info("[GITHUB] Received webhook request")

    try:
        # Get GitHub event type from header
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        logger.info(f"[GITHUB] Event type: {event_type}")

        # Log GitHub webhook details
        delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
        logger.info(f"[GITHUB] Delivery ID: {delivery_id}")

        # Process the event through the GitHub event handler
        return await cg.github.handle_webhook(request)
    except Exception as e:
        logger.error(f"[GITHUB] Error processing webhook: {str(e)}")
        # Return a 200 OK response to avoid GitHub retrying
        return Response(status_code=200)


@cg.slack.event("app_mention")
async def handle_mention(event: SlackEvent):
    """Handle mentions in Slack and respond with CodeAgent."""
    logger.info("[APP_MENTION] Received app_mention event")
    logger.info(event)

    # Codebase
    logger.info("[CODEBASE] Initializing codebase")
    codebase = cg.get_codebase()

    # Code Agent
    logger.info("[CODE_AGENT] Initializing code agent")
    agent = CodeAgent(codebase=codebase)

    logger.info("[CODE_AGENT] Running code agent")
    response = agent.run(event.text)

    # Send response back to Slack
    cg.slack.client.chat_postMessage(channel=event.channel, text=response, thread_ts=event.ts)

    # Return response for logging
    return {"message": "Mentioned", "received_text": event.text, "response": response}

@cg.github.event("pull_request:labeled")
def handle_pr_labeled(event: PullRequestLabeledEvent):
    """Handle PR labeled events and post a comment with README content."""
    logger.info("[PR_LABELED] PR labeled")
    logger.info(f"PR head sha: {event.pull_request.head.sha}")

    # Get codebase
    codebase = cg.get_codebase()

    # Checkout commit
    logger.info("> Checking out commit")
    codebase.checkout(commit=event.pull_request.head.sha)

    # Get README file
    logger.info("> Getting README file")
    file = codebase.get_file("README.md")

    # Create PR comment
    create_pr_comment(codebase, event.pull_request.number, f"File content:\n```markdown\n{file.content}\n```")

    # Notify Slack if SLACK_NOTIFICATION_CHANNEL is set
    slack_channel = os.environ.get("SLACK_NOTIFICATION_CHANNEL")
    if slack_channel:
        logger.info(f"> Notifying Slack channel {slack_channel}")
        repo_name = event.repository.full_name
        pr_number = event.pull_request.number
        pr_title = event.pull_request.title
        pr_url = event.pull_request.html_url
        label = event.label.name

        message = (
            f"*PR #{pr_number} labeled with `{label}`*\n"
            f"*Repository:* {repo_name}\n"
            f"*Title:* {pr_title}\n"
            f"*URL:* {pr_url}"
        )

        cg.slack.client.chat_postMessage(channel=slack_channel, text=message)

    return {
        "message": "PR labeled event handled",
        "num_files": len(codebase.files),
        "num_functions": len(codebase.functions)
    }

@cg.github.event("pull_request:opened")
def handle_pr_opened(event: PullRequestOpenedEvent):
    """Handle PR opened events and notify Slack."""
    logger.info("[PR_OPENED] PR opened")

    # Get codebase
    codebase = cg.get_codebase()

    # Notify Slack if SLACK_NOTIFICATION_CHANNEL is set
    slack_channel = os.environ.get("SLACK_NOTIFICATION_CHANNEL")
    if slack_channel:
        logger.info(f"> Notifying Slack channel {slack_channel}")
        repo_name = event.repository.full_name
        pr_number = event.pull_request.number
        pr_title = event.pull_request.title
        pr_url = event.pull_request.html_url
        pr_body = event.pull_request.body or "No description provided"

        message = (
            f"*New PR #{pr_number} opened*\n"
            f"*Repository:* {repo_name}\n"
            f"*Title:* {pr_title}\n"
            f"*URL:* {pr_url}\n\n"
            f"*Description:*\n{pr_body}"
        )

        cg.slack.client.chat_postMessage(channel=slack_channel, text=message)

    # Add a welcome comment to the PR
    welcome_message = "Thanks for opening this PR! :tada:\n\nI'll analyze your changes and provide feedback shortly."
    create_pr_comment(codebase, event.pull_request.number, welcome_message)

    return {
        "message": "PR opened event handled",
        "pr_number": event.pull_request.number,
        "pr_title": event.pull_request.title
    }

@cg.slack.event("message")
async def handle_message(event: SlackEvent):
    """Handle direct messages to the bot."""
    # Only process messages that are direct messages (DMs)
    # DM channels typically start with 'D'
    if not event.channel.startswith('D'):
        return {"message": "Not a DM, ignoring"}

    logger.info("[MESSAGE] Received direct message")

    # Get codebase
    codebase = cg.get_codebase()

    # Initialize code agent
    agent = CodeAgent(codebase=codebase)

    # Run the agent with the message text
    response = agent.run(event.text)

    # Send response back to Slack
    cg.slack.client.chat_postMessage(channel=event.channel, text=response, thread_ts=event.ts)

    return {"message": "DM handled", "response": response}

########################################################################################################################
# LOCAL SERVER STARTUP
########################################################################################################################

if __name__ == "__main__":
    import uvicorn

    # Log environment check
    if not os.environ.get("SLACK_BOT_TOKEN"):
        logger.warning("SLACK_BOT_TOKEN not found in environment. Slack integration may not work correctly.")

    if not os.environ.get("GITHUB_TOKEN"):
        logger.warning("GITHUB_TOKEN not found in environment. GitHub integration may not work correctly.")
        
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not found in environment. Anthropic API integration may not work correctly.")

    # Run test functions
    logger.info("Running test functions...")
    test_results = run_tests()
    logger.info(f"Test results: {test_results}")

    # Log the available routes for debugging
    logger.info("Available API routes:")
    for route in cg.app.routes:
        methods = ','.join(route.methods) if hasattr(route, "methods") else "GET"
        logger.info(f"  {methods} {route.path}")

    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))

    # Print startup message
    logger.info(f"Starting CodeGen app on 0.0.0.0:{port}")
    logger.info("For Slack integration:")
    logger.info("  1. Use ngrok: ngrok http 8000")
    logger.info("  2. Configure Slack Events API URL with: <https://your-ngrok-url/slack/events>")
    logger.info("For GitHub integration:")
    logger.info("  1. Configure GitHub webhook URL with: <https://your-ngrok-url/github/events>")
    logger.info("  2. Set content type to application/json")

    # Run the FastAPI app locally
    uvicorn.run(cg.app, host="0.0.0.0", port=port, log_level="info")

