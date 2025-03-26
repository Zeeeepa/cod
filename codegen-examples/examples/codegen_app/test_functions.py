import os
import time
import logging
import threading
import anthropic
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def send_slack_startup_message(delay=30):
    """
    Send a message to Slack after a specified delay.
    
    Args:
        delay (int): Number of seconds to wait before sending the message.
                    Default is 30 seconds. Set to 0 to send immediately.
    """
    # Wait for the specified delay
    if delay > 0:
        logger.info(f"Waiting {delay} seconds before sending Slack message...")
        time.sleep(delay)
    
    # Get Slack credentials from environment
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_channel = os.environ.get("SLACK_NOTIFICATION_CHANNEL")
    
    if not slack_token:
        logger.error("SLACK_BOT_TOKEN not found in environment variables")
        return
    
    if not slack_channel:
        logger.error("SLACK_NOTIFICATION_CHANNEL not found in environment variables")
        return
    
    # Initialize Slack client
    client = WebClient(token=slack_token)
    
    try:
        # Send message
        response = client.chat_postMessage(
            channel=slack_channel,
            text="🚀 *Bot Started Successfully!* 🚀\nThe Slack integration is working correctly."
        )
        logger.info(f"Slack startup message sent successfully: {response['ts']}")
        return response
    except SlackApiError as e:
        logger.error(f"Error sending Slack message: {e.response['error']}")
        return None

def test_anthropic_api():
    """
    Test the Anthropic API by making a simple call and printing the response.
    """
    # Get Anthropic API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        return
    
    try:
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Make a simple API call
        logger.info("Making Anthropic API call...")
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello! Please respond with a short greeting."}
            ]
        )
        
        # Print the response
        logger.info(f"Anthropic API Response: {message.content[0].text}")
        return message.content[0].text
    except Exception as e:
        logger.error(f"Error making Anthropic API call: {str(e)}")
        return None

def run_tests():
    """
    Run all test functions.
    """
    logger.info("Starting test functions...")
    
    # Start the Slack message thread
    slack_thread = threading.Thread(target=send_slack_startup_message)
    slack_thread.daemon = True
    slack_thread.start()
    logger.info("Slack startup message scheduled (will send in 30 seconds)")
    
    # Test Anthropic API
    anthropic_response = test_anthropic_api()
    if anthropic_response:
        logger.info("Anthropic API test completed successfully")
    else:
        logger.error("Anthropic API test failed")
    
    logger.info("All tests initiated")
    
    return {
        "slack_message_scheduled": True,
        "anthropic_test_result": anthropic_response is not None,
        "anthropic_response": anthropic_response
    }

if __name__ == "__main__":
    # Run tests directly if this file is executed
    run_tests()