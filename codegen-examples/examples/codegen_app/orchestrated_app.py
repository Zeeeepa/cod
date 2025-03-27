#!/usr/bin/env python3
"""
Orchestrated Slack Bot Application with advanced message flow management.

This application demonstrates how to use the MessageOrchestrator to create
sophisticated conversation flows and manage context across messages.
"""

import logging
import os
import json
import time
import threading
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from codegen import CodeAgent, CodegenApp
from codegen.extensions.github.types.events.pull_request import PullRequestLabeledEvent, PullRequestOpenedEvent
from codegen.extensions.slack.types import SlackEvent
from codegen.extensions.tools.github.create_pr_comment import create_pr_comment

# Import the MessageOrchestrator
from message_orchestrator import (
    MessageOrchestrator, MessageContext, ConversationFlow, 
    FlowState, MessageType
)

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

# Initialize the MessageOrchestrator
orchestrator = MessageOrchestrator(cg.slack.client)

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
    return {"status": "healthy", "app": "codegen-orchestrated"}

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

# Register flow handlers for different conversation types
def handle_mention_flow(flow: ConversationFlow, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a mention flow.
    
    Args:
        flow: The conversation flow
        event: The Slack event data
        
    Returns:
        A dictionary with information about the handled event
    """
    logger.info(f"[MENTION_FLOW] Handling mention flow {flow.flow_id}")
    
    # Extract the message text
    text = event.get("text", "")
    
    # Remove the mention from the text
    if orchestrator.bot_user_id:
        text = text.replace(f"<@{orchestrator.bot_user_id}>", "").strip()
    
    # Check if this is a code-related question
    if "code" in text.lower() or "function" in text.lower() or "class" in text.lower():
        # This is a code-related question, use the CodeAgent
        try:
            # Get codebase
            codebase = cg.get_codebase()
            
            # Initialize code agent
            agent = CodeAgent(codebase=codebase)
            
            # Run the agent with the message text
            response = agent.run(text)
            
            # Send the response through the orchestrator
            orchestrator.send_message(flow, response)
            
            # Update the flow state
            orchestrator.update_flow(flow, state=FlowState.WAITING_FOR_RESPONSE)
            
            return {
                "message": "Code-related mention handled",
                "flow_id": flow.flow_id,
                "response": response
            }
        except Exception as e:
            logger.error(f"[MENTION_FLOW] Error using CodeAgent: {str(e)}")
            
            # Send a fallback response
            fallback_response = (
                "I encountered an error while processing your code-related question. "
                "Please try again with a different question or contact the administrator."
            )
            
            orchestrator.send_message(flow, fallback_response)
            
            # Update the flow state
            orchestrator.update_flow(flow, state=FlowState.ERROR)
            
            return {
                "message": "Error handling code-related mention",
                "flow_id": flow.flow_id,
                "error": str(e)
            }
    else:
        # This is a general question, use a simple response
        response = (
            f"👋 Hello! I received your mention: '{text}'\n\n"
            "I can help you with code-related questions, GitHub repositories, and more. "
            "Just let me know what you need!"
        )
        
        # Send the response through the orchestrator
        orchestrator.send_message(flow, response)
        
        # Update the flow state
        orchestrator.update_flow(flow, state=FlowState.WAITING_FOR_RESPONSE)
        
        return {
            "message": "General mention handled",
            "flow_id": flow.flow_id,
            "response": response
        }

def handle_direct_message_flow(flow: ConversationFlow, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a direct message flow.
    
    Args:
        flow: The conversation flow
        event: The Slack event data
        
    Returns:
        A dictionary with information about the handled event
    """
    logger.info(f"[DM_FLOW] Handling direct message flow {flow.flow_id}")
    
    # Extract the message text
    text = event.get("text", "")
    
    # Check if this is a help request
    if "help" in text.lower():
        # This is a help request, send a help message
        help_response = (
            "👋 Here's how I can help you:\n\n"
            "• *Code Questions*: Ask me about code, functions, classes, etc.\n"
            "• *GitHub Integration*: I can help with GitHub repositories and PRs\n"
            "• *Multi-step Workflows*: I can guide you through complex tasks\n\n"
            "Just let me know what you need!"
        )
        
        # Send the response through the orchestrator
        orchestrator.send_message(flow, help_response)
        
        # Update the flow state
        orchestrator.update_flow(flow, state=FlowState.COMPLETED)
        
        return {
            "message": "Help request handled",
            "flow_id": flow.flow_id,
            "response": help_response
        }
    # Check if this is a multi-step workflow request
    elif "workflow" in text.lower() or "multi-step" in text.lower():
        # This is a multi-step workflow request, start a workflow
        workflow_response = (
            "I'll guide you through a multi-step workflow. Let's get started!\n\n"
            "*Step 1*: What type of workflow do you need help with?\n"
            "• Code Review\n"
            "• PR Creation\n"
            "• Bug Investigation\n"
        )
        
        # Send the response through the orchestrator
        orchestrator.send_message(flow, workflow_response)
        
        # Update the flow state and metadata
        orchestrator.update_flow(
            flow, 
            state=FlowState.WAITING_FOR_RESPONSE,
            metadata={"workflow_step": 1}
        )
        
        return {
            "message": "Workflow started",
            "flow_id": flow.flow_id,
            "response": workflow_response
        }
    # Check if this is a continuation of a workflow
    elif flow.metadata.get("workflow_step"):
        # This is a continuation of a workflow
        workflow_step = flow.metadata.get("workflow_step")
        
        if workflow_step == 1:
            # Process step 1 response
            if "code review" in text.lower():
                workflow_response = (
                    "Great! Let's set up a code review workflow.\n\n"
                    "*Step 2*: Please provide the GitHub repository URL or name."
                )
                
                # Update the flow metadata
                orchestrator.update_flow(
                    flow, 
                    state=FlowState.WAITING_FOR_RESPONSE,
                    metadata={"workflow_step": 2, "workflow_type": "code_review"}
                )
            elif "pr creation" in text.lower():
                workflow_response = (
                    "Great! Let's set up a PR creation workflow.\n\n"
                    "*Step 2*: Please provide the GitHub repository URL or name."
                )
                
                # Update the flow metadata
                orchestrator.update_flow(
                    flow, 
                    state=FlowState.WAITING_FOR_RESPONSE,
                    metadata={"workflow_step": 2, "workflow_type": "pr_creation"}
                )
            elif "bug investigation" in text.lower():
                workflow_response = (
                    "Great! Let's set up a bug investigation workflow.\n\n"
                    "*Step 2*: Please describe the bug you're experiencing."
                )
                
                # Update the flow metadata
                orchestrator.update_flow(
                    flow, 
                    state=FlowState.WAITING_FOR_RESPONSE,
                    metadata={"workflow_step": 2, "workflow_type": "bug_investigation"}
                )
            else:
                workflow_response = (
                    "I didn't recognize that workflow type. Please choose one of the following:\n\n"
                    "• Code Review\n"
                    "• PR Creation\n"
                    "• Bug Investigation\n"
                )
                
                # Keep the same workflow step
                orchestrator.update_flow(
                    flow, 
                    state=FlowState.WAITING_FOR_RESPONSE
                )
            
            # Send the response through the orchestrator
            orchestrator.send_message(flow, workflow_response)
            
            return {
                "message": "Workflow step 1 processed",
                "flow_id": flow.flow_id,
                "response": workflow_response
            }
        elif workflow_step == 2:
            # Process step 2 response
            workflow_type = flow.metadata.get("workflow_type")
            
            if workflow_type == "code_review":
                workflow_response = (
                    f"Thanks for providing the repository information: '{text}'\n\n"
                    "*Step 3*: Please provide the branch or PR number you want to review."
                )
                
                # Update the flow metadata
                orchestrator.update_flow(
                    flow, 
                    state=FlowState.WAITING_FOR_RESPONSE,
                    metadata={"workflow_step": 3, "repository": text}
                )
            elif workflow_type == "pr_creation":
                workflow_response = (
                    f"Thanks for providing the repository information: '{text}'\n\n"
                    "*Step 3*: Please provide the branch name for the PR."
                )
                
                # Update the flow metadata
                orchestrator.update_flow(
                    flow, 
                    state=FlowState.WAITING_FOR_RESPONSE,
                    metadata={"workflow_step": 3, "repository": text}
                )
            elif workflow_type == "bug_investigation":
                workflow_response = (
                    f"Thanks for describing the bug: '{text}'\n\n"
                    "*Step 3*: Please provide any error messages or logs you're seeing."
                )
                
                # Update the flow metadata
                orchestrator.update_flow(
                    flow, 
                    state=FlowState.WAITING_FOR_RESPONSE,
                    metadata={"workflow_step": 3, "bug_description": text}
                )
            
            # Send the response through the orchestrator
            orchestrator.send_message(flow, workflow_response)
            
            return {
                "message": "Workflow step 2 processed",
                "flow_id": flow.flow_id,
                "response": workflow_response
            }
        elif workflow_step == 3:
            # Process step 3 response and complete the workflow
            workflow_type = flow.metadata.get("workflow_type")
            
            if workflow_type == "code_review":
                workflow_response = (
                    f"Perfect! I'll set up a code review for branch/PR: '{text}'\n\n"
                    "I've recorded all the information and will process your code review request. "
                    "You'll receive a notification when the review is complete."
                )
                
                # Complete the flow
                orchestrator.complete_flow(flow, success=True, final_message=workflow_response)
            elif workflow_type == "pr_creation":
                workflow_response = (
                    f"Perfect! I'll create a PR for branch: '{text}'\n\n"
                    "I've recorded all the information and will process your PR creation request. "
                    "You'll receive a notification when the PR is created."
                )
                
                # Complete the flow
                orchestrator.complete_flow(flow, success=True, final_message=workflow_response)
            elif workflow_type == "bug_investigation":
                workflow_response = (
                    f"Thanks for providing the error information: '{text}'\n\n"
                    "I've recorded all the information and will investigate the bug. "
                    "You'll receive updates as I make progress on the investigation."
                )
                
                # Complete the flow
                orchestrator.complete_flow(flow, success=True, final_message=workflow_response)
            
            return {
                "message": "Workflow completed",
                "flow_id": flow.flow_id,
                "response": workflow_response
            }
    else:
        # This is a general message, use the CodeAgent
        try:
            # Get codebase
            codebase = cg.get_codebase()
            
            # Initialize code agent
            agent = CodeAgent(codebase=codebase)
            
            # Run the agent with the message text
            response = agent.run(text)
            
            # Send the response through the orchestrator
            orchestrator.send_message(flow, response)
            
            # Update the flow state
            orchestrator.update_flow(flow, state=FlowState.WAITING_FOR_RESPONSE)
            
            return {
                "message": "General message handled",
                "flow_id": flow.flow_id,
                "response": response
            }
        except Exception as e:
            logger.error(f"[DM_FLOW] Error using CodeAgent: {str(e)}")
            
            # Send a fallback response
            fallback_response = (
                "I encountered an error while processing your message. "
                "Please try again with a different question or contact the administrator."
            )
            
            orchestrator.send_message(flow, fallback_response)
            
            # Update the flow state
            orchestrator.update_flow(flow, state=FlowState.ERROR)
            
            return {
                "message": "Error handling general message",
                "flow_id": flow.flow_id,
                "error": str(e)
            }

# Register the flow handlers
orchestrator.register_flow_handler("mention", handle_mention_flow)
orchestrator.register_flow_handler("direct_message", handle_direct_message_flow)

async def handle_app_mention_manually(event_data):
    """
    Handle app_mention events manually using the MessageOrchestrator.
    """
    logger.info("[APP_MENTION_MANUAL] Processing app_mention event manually")
    
    # Use the orchestrator to handle the event
    result = orchestrator.handle_event(event_data)
    
    logger.info(f"[APP_MENTION_MANUAL] Orchestrator result: {result}")
    
    return Response(status_code=200)

async def handle_direct_message_manually(event_data):
    """
    Handle direct message events manually using the MessageOrchestrator.
    """
    logger.info("[DM_MANUAL] Processing direct message event manually")
    
    # Use the orchestrator to handle the event
    result = orchestrator.handle_event(event_data)
    
    logger.info(f"[DM_MANUAL] Orchestrator result: {result}")
    
    return Response(status_code=200)

@cg.slack.event("app_mention")
async def handle_mention(event: SlackEvent):
    """Handle mentions in Slack using the MessageOrchestrator."""
    logger.info("[APP_MENTION] Received app_mention event")
    
    # Convert the SlackEvent to a dictionary
    event_dict = event.__dict__
    
    # Use the orchestrator to handle the event
    result = orchestrator.handle_event(event_dict)
    
    logger.info(f"[APP_MENTION] Orchestrator result: {result}")
    
    return {"message": "Mention handled through orchestrator"}

@cg.slack.event("message")
async def handle_message(event: SlackEvent):
    """Handle direct messages to the bot using the MessageOrchestrator."""
    # Only process messages that are direct messages (DMs)
    # DM channels typically start with 'D'
    if not event.channel.startswith('D'):
        return {"message": "Not a DM, ignoring"}

    logger.info("[MESSAGE] Received direct message")
    
    # Convert the SlackEvent to a dictionary
    event_dict = event.__dict__
    
    # Use the orchestrator to handle the event
    result = orchestrator.handle_event(event_dict)
    
    logger.info(f"[MESSAGE] Orchestrator result: {result}")
    
    return {"message": "DM handled through orchestrator"}

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
            text="🚀 *Bot Started Successfully!* 🚀\nThe Slack integration is working correctly with advanced message flow orchestration."
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
    logger.info(f"Starting Orchestrated Slack Bot on 0.0.0.0:{port}")
    logger.info("For Slack integration:")
    logger.info("  1. Use ngrok: ngrok http 8000")
    logger.info("  2. Configure Slack Events API URL with: <https://your-ngrok-url/>")
    logger.info("     IMPORTANT: Use the ROOT URL, not /slack/events")
    logger.info("For GitHub integration:")
    logger.info("  1. Configure GitHub webhook URL with: <https://your-ngrok-url/github/events>")
    logger.info("  2. Set content type to application/json")

    # Run the FastAPI app locally
    uvicorn.run(cg.app, host="0.0.0.0", port=port, log_level="info")