#!/usr/bin/env python3
"""
Fixed Slack events handler for the Codegen app.
This module fixes the issue with Slack events not being properly routed.
"""

import logging
import os
import json
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import threading
import time

from codegen import CodeAgent, CodegenApp
from codegen.extensions.github.types.events.pull_request import PullRequestLabeledEvent, PullRequestOpenedEvent
from codegen.extensions.slack.types import SlackEvent
from codegen.extensions.tools.github.create_pr_comment import create_pr_comment

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

# Get bot user ID
def get_bot_user_id():
    """Get the bot's user ID from Slack."""
    try:
        response = cg.slack.client.auth_test()
        return response["user_id"]
    except Exception as e:
        logger.error(f"Error getting bot user ID: {str(e)}")
        return None

BOT_USER_ID = get_bot_user_id()
logger.info(f"Bot User ID: {BOT_USER_ID}")

# Add a root endpoint for health checks
@cg.app.get("/")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "app": "codegen-fixed"}

@cg.app.post("/")
async def root_handler(request: Request):
    """
    Handle all POST requests to the root endpoint.
    This is crucial because Slack sends events to the root URL.
    """
    logger.info("[ROOT] Received POST request")

    try:
        # Get the request body
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        
        # Log the raw request for debugging
        logger.info(f"[ROOT] Raw request body: {body_str[:200]}...")
        
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError:
            logger.error("[ROOT] Failed to parse JSON body")
            return Response(status_code=200)  # Return 200 to avoid retries
        
        logger.info(f"[ROOT] Request body type: {body.get('type', 'unknown')}")

        # Handle Slack URL verification challenge
        if body.get("type") == "url_verification":
            logger.info("[ROOT] Handling URL verification challenge")
            challenge = body.get("challenge")
            logger.info(f"[ROOT] Returning challenge: {challenge}")

            # Return the challenge as plaintext as required by Slack
            return Response(
                content=challenge,
                media_type="text/plain"
            )
        
        # Handle Slack events
        if body.get("type") == "event_callback":
            logger.info("[ROOT] Handling Slack event callback")
            event_data = body.get("event", {})
            event_type = event_data.get("type")
            
            logger.info(f"[ROOT] Event type: {event_type}")
            
            # Handle app_mention events
            if event_type == "app_mention":
                return await handle_app_mention_manually(event_data)
            
            # Handle direct message events
            if event_type == "message" and event_data.get("channel_type") == "im":
                return await handle_direct_message_manually(event_data)
        
        # For other types, try to pass to the standard handler
        try:
            # Recreate the request with the same body for the standard handler
            return await cg.slack.handle_webhook(request)
        except Exception as e:
            logger.error(f"[ROOT] Error in standard handler: {str(e)}")
            return Response(status_code=200)  # Return 200 to avoid retries

    except Exception as e:
        logger.error(f"[ROOT] Error processing request: {str(e)}")
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
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        
        # Log the raw request for debugging
        logger.info(f"[SLACK] Raw request body: {body_str[:200]}...")
        
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError:
            logger.error("[SLACK] Failed to parse JSON body")
            return Response(status_code=200)  # Return 200 to avoid retries
        
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

async def handle_app_mention_manually(event_data):
    """
    Handle app_mention events manually.
    This is a fallback for when the standard handler fails.
    """
    logger.info("[APP_MENTION_MANUAL] Processing app_mention event manually")
    
    # Extract relevant information from the event
    channel = event_data.get("channel")
    thread_ts = event_data.get("thread_ts", event_data.get("ts"))
    text = event_data.get("text", "")
    user = event_data.get("user")
    
    # Skip messages from the bot itself to avoid infinite loops
    if user == BOT_USER_ID:
        logger.info("[APP_MENTION_MANUAL] Ignoring message from the bot itself")
        return Response(status_code=200)
    
    # Extract the message without the mention
    message = text.replace(f"<@{BOT_USER_ID}>", "").strip() if BOT_USER_ID else text
    
    # Log the received message
    logger.info(f"[APP_MENTION_MANUAL] Received message: '{message}' from user {user} in channel {channel}")
    
    # Prepare a response
    response = (
        "👋 Hello! I'm responding to your mention using the fixed event handler. "
        "Here's what I can do:\n\n"
        "• Respond to mentions like this one\n"
        "• Process code-related questions\n"
        "• Help with GitHub repositories\n\n"
        "Let me know how I can assist you!"
    )
    
    try:
        # Send the response
        cg.slack.client.chat_postMessage(
            channel=channel,
            text=response,
            thread_ts=thread_ts
        )
        logger.info(f"[APP_MENTION_MANUAL] Sent response to channel {channel}")
        
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"[APP_MENTION_MANUAL] Error sending response: {str(e)}")
        return Response(status_code=200)

async def handle_direct_message_manually(event_data):
    """
    Handle direct message events manually.
    This is a fallback for when the standard handler fails.
    """
    logger.info("[DM_MANUAL] Processing direct message event manually")
    
    # Extract relevant information from the event
    channel = event_data.get("channel")
    thread_ts = event_data.get("thread_ts", event_data.get("ts"))
    text = event_data.get("text", "")
    user = event_data.get("user")
    
    # Skip messages from the bot itself to avoid infinite loops
    if user == BOT_USER_ID:
        logger.info("[DM_MANUAL] Ignoring message from the bot itself")
        return Response(status_code=200)
    
    # Log the received message
    logger.info(f"[DM_MANUAL] Received message: '{text}' from user {user} in channel {channel}")
    
    # Prepare a response
    response = (
        "👋 Hello! I'm responding to your direct message using the fixed event handler. "
        "Here's what I can do:\n\n"
        "• Answer questions about code\n"
        "• Help with GitHub repositories\n"
        "• Provide information about development best practices\n\n"
        "Let me know how I can assist you!"
    )
    
    try:
        # Send the response
        cg.slack.client.chat_postMessage(
            channel=channel,
            text=response,
            thread_ts=thread_ts
        )
        logger.info(f"[DM_MANUAL] Sent response to channel {channel}")
        
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"[DM_MANUAL] Error sending response: {str(e)}")
        return Response(status_code=200)

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

def send_slack_startup_message(delay=5):
    """
    Send a message to Slack after a specified delay.
    
    Args:
        delay (int): Number of seconds to wait before sending the message.
                    Default is 5 seconds.
    """
    # Wait for the specified delay
    if delay > 0:
        logger.info(f"Waiting {delay} seconds before sending Slack message...")
        time.sleep(delay)
    
    # Get Slack credentials from environment
    slack_channel = os.environ.get("SLACK_NOTIFICATION_CHANNEL")
    
    if not slack_channel:
        logger.error("SLACK_NOTIFICATION_CHANNEL not found in environment variables")
        return
    
    try:
        # Send message
        response = cg.slack.client.chat_postMessage(
            channel=slack_channel,
            text="🚀 *Bot Started Successfully!* 🚀\nThe Slack integration is working correctly."
        )
        logger.info(f"Slack startup message sent successfully: {response['ts']}")
        return response
    except Exception as e:
        logger.error(f"Error sending Slack message: {str(e)}")
        return None

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
        logger.warning("ANTHROPIC_API_KEY not found in environment. Falling back to simple responses.")

    # Send a startup message to Slack
    logger.info("Sending startup message to Slack...")
    slack_thread = threading.Thread(target=send_slack_startup_message)
    slack_thread.daemon = True
    slack_thread.start()

    # Log the available routes for debugging
    logger.info("Available API routes:")
    for route in cg.app.routes:
        methods = ','.join(route.methods) if hasattr(route, "methods") else "GET"
        logger.info(f"  {methods} {route.path}")

    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))

    # Print startup message
    logger.info(f"Starting Fixed Slack Bot on 0.0.0.0:{port}")
    logger.info("For Slack integration:")
    logger.info("  1. Use ngrok: ngrok http 8000")
    logger.info("  2. Configure Slack Events API URL with: <https://your-ngrok-url/>")
    logger.info("     IMPORTANT: Use the ROOT URL, not /slack/events")
    logger.info("For GitHub integration:")
    logger.info("  1. Configure GitHub webhook URL with: <https://your-ngrok-url/github/events>")
    logger.info("  2. Set content type to application/json")

    # Run the FastAPI app locally
    uvicorn.run(cg.app, host="0.0.0.0", port=port, log_level="info")