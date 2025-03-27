#!/usr/bin/env python3
"""
Agent Creator Module

This module provides functionality to create specialized code agents that can
leverage the full range of codegen tools for code modification and analysis.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum

from codegen import CodeAgent, Codebase
from codegen.extensions.langchain.agent import (
    create_codebase_agent,
    create_chat_agent,
    create_codebase_inspector_agent,
    create_agent_with_tools
)
from codegen.extensions.langchain.tools import (
    CreateFileTool,
    DeleteFileTool,
    GlobalReplacementEditTool,
    ListDirectoryTool,
    MoveSymbolTool,
    ReflectionTool,
    RelaceEditTool,
    RenameFileTool,
    ReplacementEditTool,
    RevealSymbolTool,
    RipGrepTool,
    SearchFilesByNameTool,
    ViewFileTool,
)
from langchain.tools import BaseTool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentType(Enum):
    """Types of agents that can be created."""
    CODER = "coder"  # Full-featured code modification agent
    REVIEWER = "reviewer"  # Code review agent
    INSPECTOR = "inspector"  # Read-only code inspection agent
    ORCHESTRATOR = "orchestrator"  # Message flow orchestrator
    CUSTOM = "custom"  # Custom agent with specific tools

class AgentCreator:
    """
    Creates specialized code agents with different capabilities.
    
    This class provides factory methods to create different types of agents:
    - Coder: Full-featured agent with all code modification tools
    - Reviewer: Agent specialized for code review
    - Inspector: Read-only agent for code inspection
    - Orchestrator: Agent for managing message flows
    - Custom: Agent with custom-selected tools
    """
    
    def __init__(self, repo_name: Optional[str] = None):
        """
        Initialize the AgentCreator.
        
        Args:
            repo_name: Optional name of the repository to initialize
        """
        self.repo_name = repo_name
        self.codebase = None
        
        # Initialize codebase if repo_name is provided
        if repo_name:
            self.initialize_codebase(repo_name)
    
    def initialize_codebase(self, repo_name: str) -> Codebase:
        """
        Initialize a codebase for the specified repository.
        
        Args:
            repo_name: Name of the repository to initialize
            
        Returns:
            The initialized codebase
        """
        logger.info(f"Initializing codebase for repository: {repo_name}")
        self.codebase = Codebase(repo=repo_name)
        self.repo_name = repo_name
        return self.codebase
    
    def create_agent(
        self, 
        agent_type: Union[AgentType, str],
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        tools: Optional[List[BaseTool]] = None,
        **kwargs
    ) -> CodeAgent:
        """
        Create a code agent of the specified type.
        
        Args:
            agent_type: Type of agent to create (from AgentType enum or string)
            model_provider: The model provider to use ("anthropic" or "openai")
            model_name: Name of the model to use
            memory: Whether to let LLM keep track of the conversation history
            tools: Additional tools to use (for custom agents)
            **kwargs: Additional LLM configuration options
            
        Returns:
            The created CodeAgent
        """
        # Ensure we have a codebase
        if not self.codebase:
            raise ValueError("Codebase not initialized. Call initialize_codebase() first.")
        
        # Convert string to enum if needed
        if isinstance(agent_type, str):
            try:
                agent_type = AgentType(agent_type.lower())
            except ValueError:
                raise ValueError(f"Invalid agent type: {agent_type}. Must be one of {[t.value for t in AgentType]}")
        
        # Create the appropriate agent based on type
        if agent_type == AgentType.CODER:
            return self._create_coder_agent(model_provider, model_name, memory, **kwargs)
        elif agent_type == AgentType.REVIEWER:
            return self._create_reviewer_agent(model_provider, model_name, memory, **kwargs)
        elif agent_type == AgentType.INSPECTOR:
            return self._create_inspector_agent(model_provider, model_name, memory, **kwargs)
        elif agent_type == AgentType.CUSTOM:
            if not tools:
                raise ValueError("Tools must be provided for custom agent")
            return self._create_custom_agent(tools, model_provider, model_name, memory, **kwargs)
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")
    
    def _create_coder_agent(
        self, 
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        **kwargs
    ) -> CodeAgent:
        """
        Create a full-featured code modification agent.
        
        Args:
            model_provider: The model provider to use
            model_name: Name of the model to use
            memory: Whether to enable conversation memory
            **kwargs: Additional LLM configuration options
            
        Returns:
            The created CodeAgent
        """
        logger.info(f"Creating coder agent with {model_provider}/{model_name}")
        
        # Create a full-featured agent with all code modification tools
        return CodeAgent(
            codebase=self.codebase,
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            **kwargs
        )
    
    def _create_reviewer_agent(
        self, 
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        **kwargs
    ) -> CodeAgent:
        """
        Create a code review agent.
        
        Args:
            model_provider: The model provider to use
            model_name: Name of the model to use
            memory: Whether to enable conversation memory
            **kwargs: Additional LLM configuration options
            
        Returns:
            The created CodeAgent
        """
        logger.info(f"Creating reviewer agent with {model_provider}/{model_name}")
        
        # Define review-specific tools
        review_tools = [
            ViewFileTool(self.codebase),
            ListDirectoryTool(self.codebase),
            RipGrepTool(self.codebase),
            SearchFilesByNameTool(self.codebase),
            RevealSymbolTool(self.codebase),
            ReflectionTool(self.codebase),
        ]
        
        # Create a review-focused agent
        return CodeAgent(
            codebase=self.codebase,
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            tools=review_tools,
            **kwargs
        )
    
    def _create_inspector_agent(
        self, 
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        **kwargs
    ) -> CodeAgent:
        """
        Create a read-only code inspection agent.
        
        Args:
            model_provider: The model provider to use
            model_name: Name of the model to use
            memory: Whether to enable conversation memory
            **kwargs: Additional LLM configuration options
            
        Returns:
            The created CodeAgent
        """
        logger.info(f"Creating inspector agent with {model_provider}/{model_name}")
        
        # Use the built-in inspector agent creator
        agent = create_codebase_inspector_agent(
            codebase=self.codebase,
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            **kwargs
        )
        
        # Wrap in CodeAgent
        return CodeAgent(
            codebase=self.codebase,
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            **kwargs
        )
    
    def _create_custom_agent(
        self,
        tools: List[BaseTool],
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        **kwargs
    ) -> CodeAgent:
        """
        Create a custom agent with specific tools.
        
        Args:
            tools: List of tools to provide to the agent
            model_provider: The model provider to use
            model_name: Name of the model to use
            memory: Whether to enable conversation memory
            **kwargs: Additional LLM configuration options
            
        Returns:
            The created CodeAgent
        """
        logger.info(f"Creating custom agent with {len(tools)} tools")
        
        # Create a custom agent with the specified tools
        return CodeAgent(
            codebase=self.codebase,
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            tools=tools,
            **kwargs
        )
    
    def get_available_tools(self) -> Dict[str, BaseTool]:
        """
        Get all available tools that can be used with agents.
        
        Returns:
            Dictionary of tool name to tool instance
        """
        # Ensure we have a codebase
        if not self.codebase:
            raise ValueError("Codebase not initialized. Call initialize_codebase() first.")
        
        # Create instances of all available tools
        tools = {
            "view_file": ViewFileTool(self.codebase),
            "list_directory": ListDirectoryTool(self.codebase),
            "ripgrep_search": RipGrepTool(self.codebase),
            "create_file": CreateFileTool(self.codebase),
            "delete_file": DeleteFileTool(self.codebase),
            "rename_file": RenameFileTool(self.codebase),
            "move_symbol": MoveSymbolTool(self.codebase),
            "reveal_symbol": RevealSymbolTool(self.codebase),
            "relace_edit": RelaceEditTool(self.codebase),
            "replacement_edit": ReplacementEditTool(self.codebase),
            "global_replacement": GlobalReplacementEditTool(self.codebase),
            "search_files_by_name": SearchFilesByNameTool(self.codebase),
            "reflection": ReflectionTool(self.codebase),
        }
        
        return tools
    
    def create_custom_tool_set(self, tool_names: List[str]) -> List[BaseTool]:
        """
        Create a custom set of tools by name.
        
        Args:
            tool_names: List of tool names to include
            
        Returns:
            List of tool instances
        """
        available_tools = self.get_available_tools()
        
        # Validate tool names
        invalid_tools = set(tool_names) - set(available_tools.keys())
        if invalid_tools:
            raise ValueError(f"Invalid tool names: {invalid_tools}. Available tools: {list(available_tools.keys())}")
        
        # Create the custom tool set
        return [available_tools[name] for name in tool_names]


# Example usage
if __name__ == "__main__":
    # Initialize the agent creator with a repository
    creator = AgentCreator(repo_name="Zeeeepa/cod")
    
    # Create a coder agent
    coder_agent = creator.create_agent(AgentType.CODER)
    
    # Create a reviewer agent
    reviewer_agent = creator.create_agent(AgentType.REVIEWER)
    
    # Create a custom agent with specific tools
    custom_tools = creator.create_custom_tool_set([
        "view_file", 
        "list_directory", 
        "ripgrep_search", 
        "reflection"
    ])
    custom_agent = creator.create_agent(
        AgentType.CUSTOM, 
        tools=custom_tools,
        model_provider="openai",
        model_name="gpt-4o"
    )
    
    # Run the agent with a prompt
    response = coder_agent.run("Analyze the structure of this codebase and summarize the main components.")
    print(response)