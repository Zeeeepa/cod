# Message Flow & Context Orchestrator for Slack Bot

This module provides advanced message flow management and context orchestration for Slack bots, enabling more sophisticated conversation patterns and multi-step workflows.

## Key Features

- **Conversation State Tracking**: Track the state of conversations across multiple messages
- **Context Persistence**: Maintain context across messages in a conversation
- **Multi-step Workflows**: Create guided, multi-step interactions with users
- **Timeout Handling**: Automatically handle conversations that time out
- **Message Sequence Management**: Manage sequences of messages in a conversation
- **Interactive Component Handling**: Process interactive components like buttons and menus

## Architecture

The orchestrator is built around the concept of "flows" - conversations with users that have a defined lifecycle:

1. **Flow Creation**: When a user sends a message, a new flow is created
2. **Flow Processing**: The message is processed based on the flow type
3. **Flow Continuation**: When the user responds, the conversation continues
4. **Flow Completion**: The conversation eventually completes or times out

Each flow maintains its own state and context, allowing for complex interactions.

## Components

### MessageOrchestrator

The main class that manages message flows and conversation context.

```python
orchestrator = MessageOrchestrator(slack_client)
```

### MessageContext

Contains context information for a message, such as the user ID, channel ID, and thread timestamp.

```python
context = MessageContext(
    user_id="U12345",
    channel_id="C67890",
    thread_ts="1234567890.123456"
)
```

### ConversationFlow

Represents a conversation flow with a user, including its state, messages, and metadata.

```python
flow = ConversationFlow(
    flow_id="abc123",
    context=context,
    state=FlowState.INITIATED
)
```

### FlowState

Enum representing the possible states of a conversation flow:

- `INITIATED`: The flow has been created
- `WAITING_FOR_RESPONSE`: The bot is waiting for a response from the user
- `PROCESSING`: The bot is processing a message from the user
- `COMPLETED`: The flow has completed successfully
- `TIMED_OUT`: The flow has timed out due to inactivity
- `ERROR`: An error occurred during the flow

### MessageType

Enum representing the types of messages that can be sent or received:

- `TEXT`: Plain text message
- `INTERACTIVE`: Message with interactive components
- `FILE`: Message with a file attachment
- `THREAD`: Message in a thread
- `DIRECT`: Direct message to the bot
- `CHANNEL`: Message in a channel
- `MENTION`: Mention of the bot in a channel

## Usage

### Basic Setup

```python
from slack_sdk import WebClient
from message_orchestrator import MessageOrchestrator

# Initialize the Slack client
slack_client = WebClient(token="xoxb-your-token")

# Initialize the orchestrator
orchestrator = MessageOrchestrator(slack_client)
```

### Registering Flow Handlers

```python
# Define a handler for mention flows
def handle_mention_flow(flow, event):
    # Process the mention
    # ...
    return {"message": "Mention handled"}

# Define a handler for direct message flows
def handle_dm_flow(flow, event):
    # Process the direct message
    # ...
    return {"message": "DM handled"}

# Register the handlers
orchestrator.register_flow_handler("mention", handle_mention_flow)
orchestrator.register_flow_handler("direct_message", handle_dm_flow)
```

### Handling Events

```python
# When an event is received from Slack
event = {
    "type": "app_mention",
    "user": "U12345",
    "channel": "C67890",
    "text": "<@BOTID> Hello!",
    "ts": "1234567890.123456"
}

# Handle the event
result = orchestrator.handle_event(event)
```

### Creating Multi-step Workflows

```python
def handle_workflow_flow(flow, event):
    # Check if this is the start of the workflow
    if flow.state == FlowState.INITIATED:
        # Send the first step
        orchestrator.send_message(
            flow,
            "Let's start the workflow. Step 1: What's your name?"
        )
        
        # Update the flow state and metadata
        orchestrator.update_flow(
            flow,
            state=FlowState.WAITING_FOR_RESPONSE,
            metadata={"step": 1}
        )
        
        return {"message": "Workflow started"}
    
    # Check if this is a continuation of the workflow
    elif flow.state == FlowState.WAITING_FOR_RESPONSE:
        step = flow.metadata.get("step", 1)
        
        if step == 1:
            # Process step 1 response
            name = event.get("text", "")
            
            # Send step 2
            orchestrator.send_message(
                flow,
                f"Nice to meet you, {name}! Step 2: What can I help you with?"
            )
            
            # Update the flow metadata
            orchestrator.update_flow(
                flow,
                metadata={"step": 2, "name": name}
            )
            
            return {"message": "Step 1 processed"}
        
        elif step == 2:
            # Process step 2 response and complete the workflow
            help_request = event.get("text", "")
            name = flow.metadata.get("name", "")
            
            # Complete the flow
            orchestrator.complete_flow(
                flow,
                success=True,
                final_message=f"Thanks, {name}! I'll help you with: {help_request}"
            )
            
            return {"message": "Workflow completed"}
```

## Integration with FastAPI

The orchestrator can be easily integrated with FastAPI for handling Slack events:

```python
from fastapi import FastAPI, Request, Response
from slack_sdk import WebClient
from message_orchestrator import MessageOrchestrator

app = FastAPI()
slack_client = WebClient(token="xoxb-your-token")
orchestrator = MessageOrchestrator(slack_client)

@app.post("/slack/events")
async def slack_events(request: Request):
    # Get the request body
    body = await request.json()
    
    # Handle URL verification
    if body.get("type") == "url_verification":
        return Response(
            content=body.get("challenge"),
            media_type="text/plain"
        )
    
    # Handle events
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        orchestrator.handle_event(event)
    
    return Response(status_code=200)
```

## Advanced Features

### Timeout Handling

The orchestrator automatically checks for timed-out conversations and can send a timeout message to the user:

```python
# Create a flow with a custom timeout
flow = orchestrator.create_flow(
    context,
    flow_type="custom",
    timeout_seconds=1800  # 30 minutes
)

# Disable timeout messages
orchestrator.update_flow(
    flow,
    metadata={"send_timeout_message": False}
)
```

### Interactive Messages

The orchestrator can handle interactive messages with buttons, menus, etc.:

```python
# Send an interactive message
blocks = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Choose an option:"
        }
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Option 1"
                },
                "value": "option_1",
                "action_id": "option_1"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Option 2"
                },
                "value": "option_2",
                "action_id": "option_2"
            }
        ]
    }
]

orchestrator.send_interactive_message(
    flow,
    "Choose an option:",
    blocks
)

# Handle the interaction
def handle_interaction(flow, payload):
    # Get the selected option
    action = payload.get("actions", [{}])[0]
    action_id = action.get("action_id")
    
    if action_id == "option_1":
        orchestrator.send_message(flow, "You selected Option 1")
    elif action_id == "option_2":
        orchestrator.send_message(flow, "You selected Option 2")
    
    return {"message": "Interaction handled"}

orchestrator.register_flow_handler("block_actions", handle_interaction)
```

## Example Application

See `orchestrated_app.py` for a complete example of how to use the message orchestrator in a Slack bot application.

## Benefits Over Standard Slack Handlers

1. **Stateful Conversations**: Maintain conversation state across multiple messages
2. **Context Awareness**: Keep track of the context of a conversation
3. **Multi-step Workflows**: Guide users through complex workflows step by step
4. **Timeout Handling**: Automatically handle conversations that time out
5. **Unified Event Handling**: Handle all types of events (mentions, DMs, interactions) in a consistent way
6. **Metadata Storage**: Store and retrieve metadata about conversations
7. **Flow Tracking**: Track the lifecycle of conversations from start to finish

## Getting Started

1. Copy the `message_orchestrator.py` file to your project
2. Initialize the orchestrator with your Slack client
3. Register handlers for different flow types
4. Use the orchestrator to handle Slack events

See the example application for a complete implementation.