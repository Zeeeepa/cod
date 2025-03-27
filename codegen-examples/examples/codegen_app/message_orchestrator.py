#!/usr/bin/env python3
"""
Message Flow & Context Orchestrator for Slack Bot Integration.

This module provides advanced message flow management and context orchestration
for Slack bots, enabling more sophisticated conversation patterns and workflows.
"""

import logging
import os
import json
import time
import threading
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be sent or received."""
    TEXT = "text"
    INTERACTIVE = "interactive"
    FILE = "file"
    THREAD = "thread"
    DIRECT = "direct"
    CHANNEL = "channel"
    MENTION = "mention"


class FlowState(Enum):
    """States for a conversation flow."""
    INITIATED = "initiated"
    WAITING_FOR_RESPONSE = "waiting_for_response"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    ERROR = "error"


@dataclass
class MessageContext:
    """Context information for a message."""
    user_id: str
    channel_id: str
    thread_ts: Optional[str] = None
    message_ts: Optional[str] = None
    team_id: Optional[str] = None
    is_im: bool = False
    is_mention: bool = False
    raw_event: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationFlow:
    """Represents a conversation flow with a user."""
    flow_id: str
    context: MessageContext
    state: FlowState = FlowState.INITIATED
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    timeout_seconds: int = 3600  # Default timeout of 1 hour
    handlers: Dict[str, Callable] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageOrchestrator:
    """
    Orchestrates message flows and manages conversation context.
    
    This class provides advanced message handling capabilities:
    - Conversation state tracking
    - Context persistence across messages
    - Multi-step workflows
    - Timeout handling
    - Message sequence management
    - Interactive component handling
    """
    
    def __init__(self, slack_client: WebClient):
        """
        Initialize the message orchestrator.
        
        Args:
            slack_client: The Slack WebClient instance
        """
        self.client = slack_client
        self.bot_user_id = self._get_bot_user_id()
        self.notification_channel = os.environ.get("SLACK_NOTIFICATION_CHANNEL")
        
        # Active conversation flows
        self.active_flows: Dict[str, ConversationFlow] = {}
        
        # Flow handlers for different conversation types
        self.flow_handlers: Dict[str, Callable] = {}
        
        # Start the timeout checker thread
        self._start_timeout_checker()
    
    def _get_bot_user_id(self) -> Optional[str]:
        """
        Get the bot's user ID from Slack.
        
        Returns:
            The bot's user ID or None if it couldn't be retrieved
        """
        try:
            # Call the auth.test method to get information about the bot
            response = self.client.auth_test()
            return response["user_id"]
        except SlackApiError as e:
            logger.error(f"Error getting bot user ID: {e.response['error']}")
            return None
    
    def _start_timeout_checker(self):
        """Start a background thread to check for timed-out conversations."""
        def check_timeouts():
            while True:
                current_time = time.time()
                flows_to_remove = []
                
                for flow_id, flow in self.active_flows.items():
                    # Check if the flow has timed out
                    if (current_time - flow.updated_at) > flow.timeout_seconds:
                        # Handle the timeout
                        self._handle_flow_timeout(flow)
                        flows_to_remove.append(flow_id)
                
                # Remove timed-out flows
                for flow_id in flows_to_remove:
                    self.active_flows.pop(flow_id, None)
                
                # Sleep for a while before checking again
                time.sleep(60)  # Check every minute
        
        # Start the timeout checker thread
        timeout_thread = threading.Thread(target=check_timeouts)
        timeout_thread.daemon = True
        timeout_thread.start()
    
    def _handle_flow_timeout(self, flow: ConversationFlow):
        """
        Handle a timed-out conversation flow.
        
        Args:
            flow: The conversation flow that timed out
        """
        logger.info(f"[TIMEOUT] Flow {flow.flow_id} timed out after {flow.timeout_seconds} seconds")
        
        # Update the flow state
        flow.state = FlowState.TIMED_OUT
        
        # Send a timeout message if configured
        if flow.metadata.get("send_timeout_message", True):
            try:
                self.client.chat_postMessage(
                    channel=flow.context.channel_id,
                    thread_ts=flow.context.thread_ts,
                    text="This conversation has timed out due to inactivity. Please start a new conversation if you need further assistance."
                )
            except SlackApiError as e:
                logger.error(f"[TIMEOUT] Error sending timeout message: {e.response['error']}")
    
    def register_flow_handler(self, flow_type: str, handler: Callable):
        """
        Register a handler for a specific flow type.
        
        Args:
            flow_type: The type of flow to handle
            handler: The handler function
        """
        self.flow_handlers[flow_type] = handler
        logger.info(f"Registered flow handler for '{flow_type}'")
    
    def create_flow(self, context: MessageContext, flow_type: str = "default", timeout_seconds: int = 3600) -> ConversationFlow:
        """
        Create a new conversation flow.
        
        Args:
            context: The message context
            flow_type: The type of flow to create
            timeout_seconds: The number of seconds after which the flow times out
            
        Returns:
            The created conversation flow
        """
        flow_id = str(uuid.uuid4())
        
        # Create the flow
        flow = ConversationFlow(
            flow_id=flow_id,
            context=context,
            timeout_seconds=timeout_seconds,
            metadata={"flow_type": flow_type}
        )
        
        # Store the flow
        self.active_flows[flow_id] = flow
        
        logger.info(f"[FLOW] Created new flow {flow_id} of type '{flow_type}' for user {context.user_id}")
        
        return flow
    
    def get_flow(self, flow_id: str) -> Optional[ConversationFlow]:
        """
        Get a conversation flow by ID.
        
        Args:
            flow_id: The ID of the flow to get
            
        Returns:
            The conversation flow or None if not found
        """
        return self.active_flows.get(flow_id)
    
    def get_active_flow_for_context(self, context: MessageContext) -> Optional[ConversationFlow]:
        """
        Get the active flow for a message context.
        
        Args:
            context: The message context
            
        Returns:
            The active conversation flow or None if not found
        """
        # First, try to find a flow with the same thread_ts
        if context.thread_ts:
            for flow in self.active_flows.values():
                if (flow.context.thread_ts == context.thread_ts and 
                    flow.context.channel_id == context.channel_id and
                    flow.state != FlowState.COMPLETED and
                    flow.state != FlowState.ERROR and
                    flow.state != FlowState.TIMED_OUT):
                    return flow
        
        # If no flow found with thread_ts, try to find a flow with the same user in the same channel
        for flow in self.active_flows.values():
            if (flow.context.user_id == context.user_id and 
                flow.context.channel_id == context.channel_id and
                flow.state != FlowState.COMPLETED and
                flow.state != FlowState.ERROR and
                flow.state != FlowState.TIMED_OUT):
                # Only return if it's a direct message or the same thread
                if context.is_im or (flow.context.thread_ts and flow.context.thread_ts == context.thread_ts):
                    return flow
        
        return None
    
    def update_flow(self, flow: ConversationFlow, state: Optional[FlowState] = None, 
                   add_message: Optional[Dict[str, Any]] = None, 
                   metadata: Optional[Dict[str, Any]] = None) -> ConversationFlow:
        """
        Update a conversation flow.
        
        Args:
            flow: The conversation flow to update
            state: The new state for the flow
            add_message: A message to add to the flow
            metadata: Metadata to update in the flow
            
        Returns:
            The updated conversation flow
        """
        # Update the state if provided
        if state:
            flow.state = state
        
        # Add the message if provided
        if add_message:
            flow.messages.append(add_message)
        
        # Update the metadata if provided
        if metadata:
            flow.metadata.update(metadata)
        
        # Update the timestamp
        flow.updated_at = time.time()
        
        # Store the updated flow
        self.active_flows[flow.flow_id] = flow
        
        logger.info(f"[FLOW] Updated flow {flow.flow_id} to state {flow.state}")
        
        return flow
    
    def complete_flow(self, flow: ConversationFlow, success: bool = True, 
                     final_message: Optional[str] = None) -> ConversationFlow:
        """
        Complete a conversation flow.
        
        Args:
            flow: The conversation flow to complete
            success: Whether the flow completed successfully
            final_message: A final message to send to the user
            
        Returns:
            The completed conversation flow
        """
        # Update the state
        flow.state = FlowState.COMPLETED if success else FlowState.ERROR
        
        # Send a final message if provided
        if final_message:
            try:
                response = self.client.chat_postMessage(
                    channel=flow.context.channel_id,
                    thread_ts=flow.context.thread_ts,
                    text=final_message
                )
                
                # Add the message to the flow
                flow.messages.append({
                    "type": "outgoing",
                    "text": final_message,
                    "ts": response.get("ts")
                })
            except SlackApiError as e:
                logger.error(f"[FLOW] Error sending final message: {e.response['error']}")
        
        # Update the timestamp
        flow.updated_at = time.time()
        
        logger.info(f"[FLOW] Completed flow {flow.flow_id} with status {flow.state}")
        
        return flow
    
    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a Slack event and route it to the appropriate flow.
        
        Args:
            event: The Slack event data
            
        Returns:
            A dictionary with information about the handled event
        """
        # Extract event type
        event_type = event.get("type")
        
        # Skip messages from the bot itself to avoid infinite loops
        if event.get("user") == self.bot_user_id or event.get("bot_id"):
            logger.info(f"[EVENT] Ignoring message from the bot itself")
            return {"message": "Ignored bot message"}
        
        # Create a message context from the event
        context = self._create_context_from_event(event)
        
        # Check if this event is part of an existing flow
        flow = self.get_active_flow_for_context(context)
        
        if flow:
            # This event is part of an existing flow
            logger.info(f"[EVENT] Event is part of existing flow {flow.flow_id}")
            return self._continue_flow(flow, event)
        else:
            # This is a new event, create a new flow
            logger.info(f"[EVENT] Creating new flow for event")
            return self._start_new_flow(context, event)
    
    def _create_context_from_event(self, event: Dict[str, Any]) -> MessageContext:
        """
        Create a message context from a Slack event.
        
        Args:
            event: The Slack event data
            
        Returns:
            A message context
        """
        # Extract basic information
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts", event.get("ts"))
        message_ts = event.get("ts")
        team_id = event.get("team")
        
        # Determine if this is a direct message
        is_im = event.get("channel_type") == "im"
        
        # Determine if this is a mention
        is_mention = False
        if event.get("type") == "app_mention":
            is_mention = True
        elif event.get("text") and self.bot_user_id:
            is_mention = f"<@{self.bot_user_id}>" in event.get("text", "")
        
        # Create the context
        context = MessageContext(
            user_id=user_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            message_ts=message_ts,
            team_id=team_id,
            is_im=is_im,
            is_mention=is_mention,
            raw_event=event
        )
        
        return context
    
    def _start_new_flow(self, context: MessageContext, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new conversation flow.
        
        Args:
            context: The message context
            event: The Slack event data
            
        Returns:
            A dictionary with information about the handled event
        """
        # Determine the flow type based on the event
        flow_type = self._determine_flow_type(event)
        
        # Create a new flow
        flow = self.create_flow(context, flow_type)
        
        # Add the incoming message to the flow
        self.update_flow(
            flow, 
            state=FlowState.INITIATED,
            add_message={
                "type": "incoming",
                "text": event.get("text", ""),
                "ts": event.get("ts")
            }
        )
        
        # Check if we have a handler for this flow type
        if flow_type in self.flow_handlers:
            # Call the handler
            handler = self.flow_handlers[flow_type]
            return handler(flow, event)
        else:
            # No handler found, use a default response
            logger.warning(f"[FLOW] No handler found for flow type '{flow_type}'")
            return self._handle_default_flow(flow, event)
    
    def _continue_flow(self, flow: ConversationFlow, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Continue an existing conversation flow.
        
        Args:
            flow: The conversation flow
            event: The Slack event data
            
        Returns:
            A dictionary with information about the handled event
        """
        # Add the incoming message to the flow
        self.update_flow(
            flow, 
            state=FlowState.PROCESSING,
            add_message={
                "type": "incoming",
                "text": event.get("text", ""),
                "ts": event.get("ts")
            }
        )
        
        # Get the flow type
        flow_type = flow.metadata.get("flow_type", "default")
        
        # Check if we have a handler for this flow type
        if flow_type in self.flow_handlers:
            # Call the handler
            handler = self.flow_handlers[flow_type]
            return handler(flow, event)
        else:
            # No handler found, use a default response
            logger.warning(f"[FLOW] No handler found for flow type '{flow_type}'")
            return self._handle_default_flow(flow, event)
    
    def _determine_flow_type(self, event: Dict[str, Any]) -> str:
        """
        Determine the flow type based on the event.
        
        Args:
            event: The Slack event data
            
        Returns:
            The flow type
        """
        event_type = event.get("type")
        
        if event_type == "app_mention":
            return "mention"
        elif event_type == "message":
            if event.get("channel_type") == "im":
                return "direct_message"
            else:
                return "channel_message"
        else:
            return "default"
    
    def _handle_default_flow(self, flow: ConversationFlow, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a flow with no specific handler.
        
        Args:
            flow: The conversation flow
            event: The Slack event data
            
        Returns:
            A dictionary with information about the handled event
        """
        # Extract the message text
        text = event.get("text", "")
        
        # Prepare a simple response
        response = (
            "👋 Hello! I've received your message, but I don't have a specific handler for this type of conversation. "
            "Here's what I can do:\n\n"
            "• Respond to mentions\n"
            "• Process direct messages\n"
            "• Help with code-related questions\n\n"
            "Let me know how I can assist you!"
        )
        
        try:
            # Send the response
            slack_response = self.client.chat_postMessage(
                channel=flow.context.channel_id,
                thread_ts=flow.context.thread_ts,
                text=response
            )
            
            # Add the outgoing message to the flow
            self.update_flow(
                flow, 
                state=FlowState.WAITING_FOR_RESPONSE,
                add_message={
                    "type": "outgoing",
                    "text": response,
                    "ts": slack_response.get("ts")
                }
            )
            
            logger.info(f"[FLOW] Sent default response for flow {flow.flow_id}")
            
            return {
                "message": "Default flow handled",
                "flow_id": flow.flow_id,
                "response": response
            }
        except SlackApiError as e:
            logger.error(f"[FLOW] Error sending default response: {e.response['error']}")
            
            # Update the flow state
            self.update_flow(flow, state=FlowState.ERROR)
            
            return {"error": str(e.response['error'])}
    
    def send_message(self, flow: ConversationFlow, text: str, 
                    blocks: Optional[List[Dict[str, Any]]] = None, 
                    attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Send a message as part of a flow.
        
        Args:
            flow: The conversation flow
            text: The message text
            blocks: Optional Block Kit blocks
            attachments: Optional attachments
            
        Returns:
            The Slack API response
        """
        try:
            # Send the message
            response = self.client.chat_postMessage(
                channel=flow.context.channel_id,
                thread_ts=flow.context.thread_ts,
                text=text,
                blocks=blocks,
                attachments=attachments
            )
            
            # Add the outgoing message to the flow
            self.update_flow(
                flow, 
                add_message={
                    "type": "outgoing",
                    "text": text,
                    "blocks": blocks,
                    "attachments": attachments,
                    "ts": response.get("ts")
                }
            )
            
            logger.info(f"[FLOW] Sent message for flow {flow.flow_id}")
            
            return response
        except SlackApiError as e:
            logger.error(f"[FLOW] Error sending message: {e.response['error']}")
            return {"error": str(e.response['error'])}
    
    def send_interactive_message(self, flow: ConversationFlow, text: str, 
                               blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send an interactive message as part of a flow.
        
        Args:
            flow: The conversation flow
            text: The message text
            blocks: Block Kit blocks with interactive components
            
        Returns:
            The Slack API response
        """
        return self.send_message(flow, text, blocks)
    
    def update_message(self, flow: ConversationFlow, ts: str, text: str, 
                      blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Update a message as part of a flow.
        
        Args:
            flow: The conversation flow
            ts: The timestamp of the message to update
            text: The new message text
            blocks: Optional new Block Kit blocks
            
        Returns:
            The Slack API response
        """
        try:
            # Update the message
            response = self.client.chat_update(
                channel=flow.context.channel_id,
                ts=ts,
                text=text,
                blocks=blocks
            )
            
            # Update the message in the flow
            for message in flow.messages:
                if message.get("ts") == ts:
                    message["text"] = text
                    if blocks:
                        message["blocks"] = blocks
                    break
            
            # Update the flow
            self.update_flow(flow)
            
            logger.info(f"[FLOW] Updated message {ts} for flow {flow.flow_id}")
            
            return response
        except SlackApiError as e:
            logger.error(f"[FLOW] Error updating message: {e.response['error']}")
            return {"error": str(e.response['error'])}
    
    def delete_message(self, flow: ConversationFlow, ts: str) -> Dict[str, Any]:
        """
        Delete a message as part of a flow.
        
        Args:
            flow: The conversation flow
            ts: The timestamp of the message to delete
            
        Returns:
            The Slack API response
        """
        try:
            # Delete the message
            response = self.client.chat_delete(
                channel=flow.context.channel_id,
                ts=ts
            )
            
            # Remove the message from the flow
            flow.messages = [m for m in flow.messages if m.get("ts") != ts]
            
            # Update the flow
            self.update_flow(flow)
            
            logger.info(f"[FLOW] Deleted message {ts} for flow {flow.flow_id}")
            
            return response
        except SlackApiError as e:
            logger.error(f"[FLOW] Error deleting message: {e.response['error']}")
            return {"error": str(e.response['error'])}
    
    def handle_interaction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an interaction payload from Slack.
        
        Args:
            payload: The interaction payload
            
        Returns:
            A dictionary with information about the handled interaction
        """
        # Extract relevant information
        user_id = payload.get("user", {}).get("id")
        channel_id = payload.get("channel", {}).get("id")
        message_ts = payload.get("message", {}).get("ts")
        
        # Create a context for the interaction
        context = MessageContext(
            user_id=user_id,
            channel_id=channel_id,
            message_ts=message_ts,
            raw_event=payload
        )
        
        # Try to find an active flow for this context
        flow = self.get_active_flow_for_context(context)
        
        if flow:
            # This interaction is part of an existing flow
            logger.info(f"[INTERACTION] Interaction is part of existing flow {flow.flow_id}")
            
            # Update the flow with the interaction
            self.update_flow(
                flow, 
                state=FlowState.PROCESSING,
                add_message={
                    "type": "interaction",
                    "payload": payload,
                    "ts": time.time()
                }
            )
            
            # Get the flow type
            flow_type = flow.metadata.get("flow_type", "default")
            
            # Check if we have a handler for this flow type
            if flow_type in self.flow_handlers:
                # Call the handler
                handler = self.flow_handlers[flow_type]
                return handler(flow, payload)
            else:
                # No handler found, use a default response
                logger.warning(f"[FLOW] No handler found for flow type '{flow_type}'")
                return self._handle_default_interaction(flow, payload)
        else:
            # This is a new interaction, create a new flow
            logger.info(f"[INTERACTION] Creating new flow for interaction")
            
            # Determine the flow type based on the interaction
            flow_type = self._determine_interaction_flow_type(payload)
            
            # Create a new flow
            flow = self.create_flow(context, flow_type)
            
            # Add the interaction to the flow
            self.update_flow(
                flow, 
                state=FlowState.INITIATED,
                add_message={
                    "type": "interaction",
                    "payload": payload,
                    "ts": time.time()
                }
            )
            
            # Check if we have a handler for this flow type
            if flow_type in self.flow_handlers:
                # Call the handler
                handler = self.flow_handlers[flow_type]
                return handler(flow, payload)
            else:
                # No handler found, use a default response
                logger.warning(f"[FLOW] No handler found for flow type '{flow_type}'")
                return self._handle_default_interaction(flow, payload)
    
    def _determine_interaction_flow_type(self, payload: Dict[str, Any]) -> str:
        """
        Determine the flow type based on the interaction payload.
        
        Args:
            payload: The interaction payload
            
        Returns:
            The flow type
        """
        # Extract the type of interaction
        type_str = payload.get("type")
        
        if type_str == "block_actions":
            return "block_actions"
        elif type_str == "view_submission":
            return "view_submission"
        elif type_str == "view_closed":
            return "view_closed"
        else:
            return "interaction"
    
    def _handle_default_interaction(self, flow: ConversationFlow, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an interaction with no specific handler.
        
        Args:
            flow: The conversation flow
            payload: The interaction payload
            
        Returns:
            A dictionary with information about the handled interaction
        """
        # Extract the action information
        actions = payload.get("actions", [])
        action_ids = [a.get("action_id") for a in actions]
        
        # Prepare a simple response
        response = (
            "👋 I've received your interaction, but I don't have a specific handler for this type of action. "
            f"Action IDs: {', '.join(action_ids)}"
        )
        
        try:
            # Send the response
            slack_response = self.client.chat_postMessage(
                channel=flow.context.channel_id,
                thread_ts=flow.context.thread_ts,
                text=response
            )
            
            # Add the outgoing message to the flow
            self.update_flow(
                flow, 
                state=FlowState.WAITING_FOR_RESPONSE,
                add_message={
                    "type": "outgoing",
                    "text": response,
                    "ts": slack_response.get("ts")
                }
            )
            
            logger.info(f"[FLOW] Sent default interaction response for flow {flow.flow_id}")
            
            return {
                "message": "Default interaction handled",
                "flow_id": flow.flow_id,
                "response": response
            }
        except SlackApiError as e:
            logger.error(f"[FLOW] Error sending default interaction response: {e.response['error']}")
            
            # Update the flow state
            self.update_flow(flow, state=FlowState.ERROR)
            
            return {"error": str(e.response['error'])}