#!/usr/bin/env python3
"""
Standalone script to debug Anthropic API issues.
This script provides detailed error information when testing the Anthropic API.
"""

import os
import logging
import anthropic
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def debug_anthropic_api():
    """
    Test the Anthropic API with detailed error reporting.
    """
    # Get Anthropic API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        return
    
    # Log the first few characters of the API key (for debugging format issues)
    # Be careful not to log the entire key for security reasons
    key_prefix = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "too short"
    key_length = len(api_key)
    logger.info(f"API key prefix/suffix: {key_prefix}, length: {key_length}")
    
    # Check for common formatting issues
    if api_key.startswith('"') or api_key.endswith('"'):
        logger.error("API key contains quote characters - please remove them from your .env file")
        logger.info("Your .env file should contain: ANTHROPIC_API_KEY=sk-ant-api03-xxx")
        logger.info("NOT: ANTHROPIC_API_KEY=\"sk-ant-api03-xxx\"")
        return
    
    if ">" in api_key or "<" in api_key:
        logger.error("API key contains angle brackets - please remove them from your .env file")
        logger.info("Your .env file should contain: ANTHROPIC_API_KEY=sk-ant-api03-xxx")
        return
    
    if not api_key.startswith("sk-ant"):
        logger.warning("API key doesn't start with 'sk-ant' which is unusual for Anthropic keys")
    
    try:
        # Initialize Anthropic client
        logger.info("Initializing Anthropic client...")
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
        logger.error(f"Error type: {type(e).__name__}")
        
        # Provide more specific guidance based on error type
        if "401" in str(e):
            logger.error("Authentication error: Your API key is invalid or expired")
        elif "403" in str(e):
            logger.error("Authorization error: Your API key doesn't have permission to use this model")
        elif "404" in str(e):
            logger.error("Not found error: The requested resource (likely the model) doesn't exist")
        elif "429" in str(e):
            logger.error("Rate limit error: You've exceeded your API rate limits")
        elif "timeout" in str(e).lower():
            logger.error("Timeout error: The request took too long to complete")
        
        return None

if __name__ == "__main__":
    logger.info("=== ANTHROPIC API DEBUGGING TOOL ===")
    result = debug_anthropic_api()
    if result:
        logger.info("✅ Anthropic API test SUCCESSFUL")
    else:
        logger.error("❌ Anthropic API test FAILED")