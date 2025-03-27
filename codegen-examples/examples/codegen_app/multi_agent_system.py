#!/usr/bin/env python3
"""
Multi-Agent System for Code Development

This script demonstrates how to create and use a multi-agent system for code development,
leveraging the AgentCreator to create specialized agents for different tasks.
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

from codegen import Codebase
from agent_creator import AgentCreator, AgentType
from message_orchestrator import MessageOrchestrator, MessageContext, ConversationFlow, FlowState

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiAgentSystem:
    """
    A multi-agent system for code development that combines specialized agents
    for different tasks, coordinated by a message orchestrator.
    
    The system includes:
    - PR Reviewer Agent: Reviews pull requests and provides feedback
    - Message Orchestrator: Manages conversation flows and context
    - Code Agent: Modifies code based on requirements
    """
    
    def __init__(self, repo_name: str):
        """
        Initialize the multi-agent system.
        
        Args:
            repo_name: Name of the repository to work with
        """
        self.repo_name = repo_name
        self.agent_creator = AgentCreator(repo_name=repo_name)
        
        # Initialize agents
        self.pr_reviewer = self._create_pr_reviewer()
        self.code_agent = self._create_code_agent()
        
        # Store all agents in a dictionary for easy access
        self.agents = {
            "pr_reviewer": self.pr_reviewer,
            "code_agent": self.code_agent,
        }
        
        logger.info(f"Multi-agent system initialized for repository: {repo_name}")
    
    def _create_pr_reviewer(self):
        """Create a PR reviewer agent."""
        logger.info("Creating PR reviewer agent")
        return self.agent_creator.create_agent(
            agent_type=AgentType.REVIEWER,
            model_provider="anthropic",
            model_name="claude-3-7-sonnet-latest"
        )
    
    def _create_code_agent(self):
        """Create a code modification agent."""
        logger.info("Creating code agent")
        return self.agent_creator.create_agent(
            agent_type=AgentType.CODER,
            model_provider="anthropic",
            model_name="claude-3-7-sonnet-latest"
        )
    
    def create_custom_agent(self, tool_names: List[str], model_provider: str = "anthropic", model_name: str = "claude-3-7-sonnet-latest"):
        """
        Create a custom agent with specific tools.
        
        Args:
            tool_names: List of tool names to include
            model_provider: The model provider to use
            model_name: Name of the model to use
            
        Returns:
            The created agent
        """
        logger.info(f"Creating custom agent with tools: {tool_names}")
        
        # Create the custom tool set
        custom_tools = self.agent_creator.create_custom_tool_set(tool_names)
        
        # Create and return the custom agent
        return self.agent_creator.create_agent(
            agent_type=AgentType.CUSTOM,
            tools=custom_tools,
            model_provider=model_provider,
            model_name=model_name
        )
    
    def review_pr(self, pr_number: int) -> str:
        """
        Review a pull request.
        
        Args:
            pr_number: The PR number to review
            
        Returns:
            The review result
        """
        logger.info(f"Reviewing PR #{pr_number}")
        
        # Construct a prompt for the PR reviewer
        prompt = f"""
        Please review pull request #{pr_number} in the repository {self.repo_name}.
        
        Analyze the code changes and provide feedback on:
        1. Code quality and best practices
        2. Potential bugs or issues
        3. Performance considerations
        4. Documentation and comments
        
        Format your response as a structured review with sections for each of these areas.
        """
        
        # Run the PR reviewer agent
        return self.pr_reviewer.run(prompt)
    
    def modify_code(self, file_path: str, modification_description: str) -> str:
        """
        Modify code in a file based on a description.
        
        Args:
            file_path: Path to the file to modify
            modification_description: Description of the modification to make
            
        Returns:
            The result of the code modification
        """
        logger.info(f"Modifying code in {file_path}")
        
        # Construct a prompt for the code agent
        prompt = f"""
        Please modify the code in file {file_path} according to the following description:
        
        {modification_description}
        
        First, analyze the current code to understand its structure and functionality.
        Then, make the necessary changes while preserving the existing behavior unless explicitly instructed to change it.
        Finally, explain the changes you made and why.
        """
        
        # Run the code agent
        return self.code_agent.run(prompt)
    
    def analyze_codebase(self) -> str:
        """
        Analyze the structure and components of the codebase.
        
        Returns:
            Analysis of the codebase
        """
        logger.info(f"Analyzing codebase structure for {self.repo_name}")
        
        # Construct a prompt for the code agent
        prompt = """
        Please analyze the structure of this codebase and provide a comprehensive overview.
        
        Include information about:
        1. Main components and their responsibilities
        2. Key files and directories
        3. Architecture patterns used
        4. Dependencies and their purposes
        5. Entry points and execution flow
        
        Format your response as a structured analysis with sections for each of these areas.
        """
        
        # Run the code agent
        return self.code_agent.run(prompt)
    
    def get_available_tools(self) -> List[str]:
        """
        Get a list of all available tools that can be used with agents.
        
        Returns:
            List of tool names
        """
        return list(self.agent_creator.get_available_tools().keys())


# Example usage
if __name__ == "__main__":
    # Initialize the multi-agent system
    system = MultiAgentSystem(repo_name="Zeeeepa/cod")
    
    # Print available tools
    print("Available tools:")
    for tool in system.get_available_tools():
        print(f"- {tool}")
    
    # Create a custom agent for code search
    search_agent = system.create_custom_agent([
        "view_file", 
        "list_directory", 
        "ripgrep_search", 
        "search_files_by_name",
        "reflection"
    ])
    
    # Example: Analyze the codebase structure
    print("\nAnalyzing codebase structure...")
    analysis = system.analyze_codebase()
    print(analysis)
    
    # Example: Review a PR
    # Uncomment to run
    # pr_review = system.review_pr(1)
    # print(pr_review)
    
    # Example: Modify code
    # Uncomment to run
    # modification = system.modify_code(
    #     "codegen-examples/examples/codegen_app/app.py",
    #     "Add error handling to the handle_mention function to catch and log any exceptions."
    # )
    # print(modification)