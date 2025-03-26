#!/usr/bin/env python3
"""
Slack event handler module for the Codegen app.
This module provides enhanced event handling for Slack events.
"""

import logging
import os
import json
import re
from typing import Dict, Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SlackEventHandler:
    """
    Enhanced Slack event handler that ensures proper event processing.
    """
    
    def __init__(self, slack_client: WebClient):
        """
        Initialize the Slack event handler.
        
        Args:
            slack_client: The Slack WebClient instance
        """
        self.client = slack_client
        self.bot_user_id = self._get_bot_user_id()
        self.notification_channel = os.environ.get("SLACK_NOTIFICATION_CHANNEL")
        
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
    
    def is_bot_message(self, event: Dict[str, Any]) -> bool:
        """
        Check if a message was sent by this bot to avoid infinite loops.
        
        Args:
            event: The Slack event data
            
        Returns:
            True if the message was sent by this bot, False otherwise
        """
        # Check if the message was sent by the bot
        return event.get("user") == self.bot_user_id or event.get("bot_id") is not None
    
    def is_mention(self, text: str) -> bool:
        """
        Check if the message text contains a mention of the bot.
        
        Args:
            text: The message text
            
        Returns:
            True if the message contains a mention of the bot, False otherwise
        """
        if not self.bot_user_id or not text:
            return False
        
        # Check for mentions in the format <@USER_ID>
        mention_pattern = f"<@{self.bot_user_id}>"
        return mention_pattern in text
    
    def extract_message_without_mention(self, text: str) -> str:
        """
        Remove the bot mention from the message text.
        
        Args:
            text: The message text
            
        Returns:
            The message text without the bot mention
        """
        if not self.bot_user_id or not text:
            return text
        
        # Remove mentions in the format <@USER_ID>
        mention_pattern = f"<@{self.bot_user_id}>"
        return text.replace(mention_pattern, "").strip()
    
    def handle_app_mention(self, event: Dict[str, Any], use_anthropic: bool = True) -> Dict[str, Any]:
        """
        Handle app_mention events.
        
        Args:
            event: The Slack event data
            use_anthropic: Whether to use the Anthropic API for responses
            
        Returns:
            A dictionary with information about the handled event
        """
        logger.info("[APP_MENTION] Processing app_mention event")
        
        # Extract relevant information from the event
        channel = event.get("channel")
        thread_ts = event.get("thread_ts", event.get("ts"))
        text = event.get("text", "")
        user = event.get("user")
        
        # Skip messages from the bot itself to avoid infinite loops
        if self.is_bot_message(event):
            logger.info("[APP_MENTION] Ignoring message from the bot itself")
            return {"message": "Ignored bot message"}
        
        # Extract the message without the mention
        message = self.extract_message_without_mention(text)
        
        # Log the received message
        logger.info(f"[APP_MENTION] Received message: '{message}' from user {user} in channel {channel}")
        
        # Prepare a response
        if use_anthropic:
            # This would be handled by the CodeAgent in the main app
            response = "I'll process this with the Anthropic API."
        else:
            # Simple predefined response
            response = (
                "👋 Hello! I'm responding to your mention. "
                "Here's what I can do:\n\n"
                "• Respond to mentions like this one\n"
                "• Process code-related questions\n"
                "• Help with GitHub repositories\n\n"
                "Let me know how I can assist you!"
            )
        
        try:
            # Send the response
            self.client.chat_postMessage(
                channel=channel,
                text=response,
                thread_ts=thread_ts
            )
            logger.info(f"[APP_MENTION] Sent response to channel {channel}")
            
            return {
                "message": "Mention handled",
                "channel": channel,
                "user": user,
                "text": message,
                "response": response
            }
        except SlackApiError as e:
            logger.error(f"[APP_MENTION] Error sending response: {e.response['error']}")
            return {"error": str(e.response['error'])}
    
    def handle_direct_message(self, event: Dict[str, Any], use_anthropic: bool = True) -> Dict[str, Any]:
        """
        Handle direct message events.
        
        Args:
            event: The Slack event data
            use_anthropic: Whether to use the Anthropic API for responses
            
        Returns:
            A dictionary with information about the handled event
        """
        logger.info("[DM] Processing direct message event")
        
        # Extract relevant information from the event
        channel = event.get("channel")
        thread_ts = event.get("thread_ts", event.get("ts"))
        text = event.get("text", "")
        user = event.get("user")
        
        # Skip messages from the bot itself to avoid infinite loops
        if self.is_bot_message(event):
            logger.info("[DM] Ignoring message from the bot itself")
            return {"message": "Ignored bot message"}
        
        # Log the received message
        logger.info(f"[DM] Received message: '{text}' from user {user} in channel {channel}")
        
        # Prepare a response
        if use_anthropic:
            # This would be handled by the CodeAgent in the main app
            response = "I'll process this with the Anthropic API."
        else:
            # Simple predefined response
            response = (
                "👋 Hello! I'm responding to your direct message. "
                "Here's what I can do:\n\n"
                "• Answer questions about code\n"
                "• Help with GitHub repositories\n"
                "• Provide information about development best practices\n\n"
                "Let me know how I can assist you!"
            )
        
        try:
            # Send the response
            self.client.chat_postMessage(
                channel=channel,
                text=response,
                thread_ts=thread_ts
            )
            logger.info(f"[DM] Sent response to channel {channel}")
            
            return {
                "message": "DM handled",
                "channel": channel,
                "user": user,
                "text": text,
                "response": response
            }
        except SlackApiError as e:
            logger.error(f"[DM] Error sending response: {e.response['error']}")
            return {"error": str(e.response['error'])}
    
    def send_notification(self, message: str) -> Dict[str, Any]:
        """
        Send a notification to the configured notification channel.
        
        Args:
            message: The message to send
            
        Returns:
            A dictionary with information about the sent notification
        """
        if not self.notification_channel:
            logger.warning("[NOTIFICATION] No notification channel configured")
            return {"error": "No notification channel configured"}
        
        try:
            # Send the notification
            response = self.client.chat_postMessage(
                channel=self.notification_channel,
                text=message
            )
            logger.info(f"[NOTIFICATION] Sent notification to channel {self.notification_channel}")
            
            return {
                "message": "Notification sent",
                "channel": self.notification_channel,
                "ts": response.get("ts")
            }
        except SlackApiError as e:
            logger.error(f"[NOTIFICATION] Error sending notification: {e.response['error']}")
            return {"error": str(e.response['error'])}