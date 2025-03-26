#!/usr/bin/env python3
"""
Standalone script to test Slack and Anthropic API functionality.
This script can be run independently of the main application.
"""

import os
import logging
from dotenv import load_dotenv
from test_functions import send_slack_startup_message, test_anthropic_api

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Run the test functions and display results."""
    logger.info("=== TESTING SLACK AND ANTHROPIC INTEGRATION ===")
    
    # Check environment variables
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_channel = os.environ.get("SLACK_NOTIFICATION_CHANNEL")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    logger.info(f"SLACK_BOT_TOKEN present: {bool(slack_token)}")
    logger.info(f"SLACK_NOTIFICATION_CHANNEL present: {bool(slack_channel)}")
    logger.info(f"ANTHROPIC_API_KEY present: {bool(anthropic_key)}")
    
    # Test Slack
    logger.info("\n=== TESTING SLACK INTEGRATION ===")
    if slack_token and slack_channel:
        logger.info("Sending test message to Slack...")
        # Send immediately without delay
        response = send_slack_startup_message(delay=0)
        if response:
            logger.info("Slack message sent successfully!")
        else:
            logger.error("Failed to send Slack message.")
    else:
        logger.error("Slack credentials missing. Cannot test Slack integration.")
    
    # Test Anthropic
    logger.info("\n=== TESTING ANTHROPIC API ===")
    if anthropic_key:
        logger.info("Testing Anthropic API...")
        response = test_anthropic_api()
        if response:
            logger.info("Anthropic API test successful!")
            logger.info(f"Response: {response}")
        else:
            logger.error("Anthropic API test failed.")
    else:
        logger.error("Anthropic API key missing. Cannot test Anthropic integration.")
    
    logger.info("\n=== TESTS COMPLETED ===")

if __name__ == "__main__":
    main()