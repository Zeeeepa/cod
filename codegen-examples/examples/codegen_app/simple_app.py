#!/usr/bin/env python3
"""
Simple Slack bot application that doesn't require Anthropic API.
This version responds to mentions with predefined responses.
"""

import logging
import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from codegen import CodegenApp
from codegen.extensions.slack.types import SlackEvent

# Import test functions
from test_functions import send_slack_startup_message

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
    return {"status": "healthy", "app": "codegen-simple"}

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

@cg.slack.event("app_mention")
async def handle_mention(event: SlackEvent):
    """Handle mentions in Slack with a simple predefined response."""
    logger.info("[APP_MENTION] Received app_mention event")
    logger.info(event)

    # Simple predefined response that doesn't require Anthropic API
    response = (
        "👋 Hello! I'm a simple bot that can respond to mentions. "
        "I'm currently running in a mode that doesn't require the Anthropic API. "
        "Here are some things I can help with:\n\n"
        "• Respond to mentions (like this one!)\n"
        "• Send notifications about GitHub events\n"
        "• Provide basic information\n\n"
        "To use my full capabilities with AI-powered responses, please make sure your "
        "ANTHROPIC_API_KEY is correctly configured in your .env file."
    )

    # Send response back to Slack
    cg.slack.client.chat_postMessage(channel=event.channel, text=response, thread_ts=event.ts)

    # Return response for logging
    return {"message": "Mentioned", "received_text": event.text, "response": response}

@cg.slack.event("message")
async def handle_message(event: SlackEvent):
    """Handle direct messages to the bot."""
    # Only process messages that are direct messages (DMs)
    # DM channels typically start with 'D'
    if not event.channel.startswith('D'):
        return {"message": "Not a DM, ignoring"}

    logger.info("[MESSAGE] Received direct message")

    # Simple predefined response that doesn't require Anthropic API
    response = (
        "👋 Hello! I'm a simple bot that can respond to direct messages. "
        "I'm currently running in a mode that doesn't require the Anthropic API. "
        "Here are some things I can help with:\n\n"
        "• Respond to direct messages (like this one!)\n"
        "• Send notifications about GitHub events\n"
        "• Provide basic information\n\n"
        "To use my full capabilities with AI-powered responses, please make sure your "
        "ANTHROPIC_API_KEY is correctly configured in your .env file."
    )

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

    if not os.environ.get("SLACK_NOTIFICATION_CHANNEL"):
        logger.warning("SLACK_NOTIFICATION_CHANNEL not found in environment. Slack notifications may not work correctly.")

    # Send a startup message to Slack
    logger.info("Sending startup message to Slack...")
    send_slack_startup_message(delay=5)  # Send after 5 seconds

    # Log the available routes for debugging
    logger.info("Available API routes:")
    for route in cg.app.routes:
        methods = ','.join(route.methods) if hasattr(route, "methods") else "GET"
        logger.info(f"  {methods} {route.path}")

    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))

    # Print startup message
    logger.info(f"Starting Simple Slack Bot on 0.0.0.0:{port}")
    logger.info("For Slack integration:")
    logger.info("  1. Use ngrok: ngrok http 8000")
    logger.info("  2. Configure Slack Events API URL with: <https://your-ngrok-url/slack/events>")

    # Run the FastAPI app locally
    uvicorn.run(cg.app, host="0.0.0.0", port=port, log_level="info")