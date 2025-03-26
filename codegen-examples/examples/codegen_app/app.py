import logging

import modal
from codegen import CodeAgent, CodegenApp
from codegen.extensions.github.types.events.pull_request import PullRequestLabeledEvent
from codegen.extensions.linear.types import LinearEvent
from codegen.extensions.slack.types import SlackEvent
from codegen.extensions.tools.github.create_pr_comment import create_pr_comment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

########################################################################################################################
# EVENTS
########################################################################################################################

# Create the cg_app
cg = CodegenApp(name="codegen-test", repo="codegen-sh/Kevin-s-Adventure-Game")


@cg.slack.event("app_mention")
async def handle_mention(event: SlackEvent):
    logger.info("[APP_MENTION] Received cg_app_mention event")
    logger.info(event)

    # Codebase
    logger.info("[CODEBASE] Initializing codebase")
    codebase = cg.get_codebase()

    # Code Agent
    logger.info("[CODE_AGENT] Initializing code agent")
    agent = CodeAgent(codebase=codebase)

    logger.info("[CODE_AGENT] Running code agent")
    response = agent.run(event.text)

    cg.slack.client.chat_postMessage(channel=event.channel, text=response, thread_ts=event.ts)
    return {"message": "Mentioned", "received_text": event.text, "response": response}


@cg.github.event("pull_request:labeled")
def handle_pr(event: PullRequestLabeledEvent):
    logger.info("PR labeled")
    logger.info(f"PR head sha: {event.pull_request.head.sha}")
    codebase = cg.get_codebase()

    # =====[ Check out commit ]=====
    # Might require fetch?
    logger.info("> Checking out commit")
    codebase.checkout(commit=event.pull_request.head.sha)

    logger.info("> Getting files")
    file = codebase.get_file("README.md")

    # =====[ Create PR comment ]=====
    create_pr_comment(codebase, event.pull_request.number, f"File content:\n```python\n{file.content}\n```")

    return {"message": "PR event handled", "num_files": len(codebase.files), "num_functions": len(codebase.functions)}


@cg.linear.event("Issue")
def handle_issue(event: LinearEvent):
    logger.info(f"Issue created: {event}")
    codebase = cg.get_codebase()
    return {"message": "Linear Issue event", "num_files": len(codebase.files), "num_functions": len(codebase.functions)}


########################################################################################################################
# MODAL DEPLOYMENT
########################################################################################################################
# This deploys the FastAPI app to Modal
# TODO: link this up with memory snapshotting.

# For deploying local package
REPO_URL = "https://github.com/codegen-sh/codegen-sdk.git"
COMMIT_ID = "6a0e101718c247c01399c60b7abf301278a41786"

# Create the base image with dependencies
base_image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .pip_install(
        # =====[ Codegen ]=====
        # "codegen",
        f"git+{REPO_URL}@{COMMIT_ID}",
        # =====[ Rest ]=====
        "openai>=1.1.0",
        "fastapi[standard]",
        "slack_sdk",
    )
)

app = modal.App("codegen-test")


@app.function(image=base_image, secrets=[modal.Secret.from_dotenv()])
@modal.asgi_app()
def fastapi_app():
    print("Starting codegen fastapi app")
    # Configure the app routes
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import JSONResponse
    
    # Get the FastAPI app from CodegenApp
    fastapi_app = cg.app
    
    # Add a root route handler for health checks
    @fastapi_app.get("/")
    async def root():
        return {"status": "ok", "message": "Codegen app is running"}
    
    # Add explicit webhook routes for better debugging
    @fastapi_app.post("/slack/events")
    async def slack_events(request: Request):
        logger.info("Received Slack event")
        body = await request.json()
        logger.info(f"Slack event body: {body}")
        
        # Handle URL verification challenge
        if body.get("type") == "url_verification":
            logger.info("Handling Slack URL verification challenge")
            challenge = body.get("challenge")
            return JSONResponse(content={"challenge": challenge})
        
        # Forward to the CodegenApp handler
        return await cg.slack.handle_event(request)
    
    @fastapi_app.post("/github/events")
    async def github_events(request: Request):
        logger.info("Received GitHub event")
        return await cg.github.handle_event(request)
    
    @fastapi_app.post("/linear/events")
    async def linear_events(request: Request):
        logger.info("Received Linear event")
        return await cg.linear.handle_event(request)
    
    return fastapi_app
