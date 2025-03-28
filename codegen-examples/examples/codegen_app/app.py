import logging
import os
from fastapi import Request, Response
from codegen import CodeAgent, CodegenApp
from codegen.extensions.github.types.events.pull_request import PullRequestLabeledEvent, PullRequestOpenedEvent
from codegen.extensions.slack.types import SlackEvent
from codegen.extensions.tools.github.create_pr_comment import create_pr_comment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

########################################################################################################################
# EVENTS
########################################################################################################################

# Create the cg_app
cg = CodegenApp(name="code", repo="zeeeepa/cod")

# Add explicit route handlers for webhooks
@cg.app.post("/slack/events")
async def slack_webhook(request: Request):
    """Handle Slack webhook events, including URL verification."""
    logger.info("[SLACK] Received webhook request")
    
    # Get the request body
    body = await request.json()
    logger.info(f"[SLACK] Request body: {body}")
    
    # Handle Slack URL verification challenge
    if body.get("type") == "url_verification":
        logger.info("[SLACK] Handling URL verification challenge")
        challenge = body.get("challenge")
        return {"challenge": challenge}
    
    # Process the event through the normal event handlers
    return await cg.slack.handle_webhook(request)

@cg.app.post("/github/events")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    logger.info("[GITHUB] Received webhook request")
    return await cg.github.handle_webhook(request)

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
    welcome_message = "Thanks for opening this PR! 🎉\n\nI'll analyze your changes and provide feedback shortly."
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


def fastapi_app():
    print("Starting codegen fastapi app")
    return cg.app
