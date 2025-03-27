#!/usr/bin/env python3
"""
Enhanced Coder Agent Module

This module provides an enhanced coder agent that leverages advanced codebase analysis
capabilities to provide more sophisticated code modifications and recommendations.
"""

import logging
import os
import time
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

from codebase_analyzer import CodebaseAnalyzer, AnalysisType, AnalysisResult

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedCoderAgent:
    """
    Enhanced coder agent that leverages advanced codebase analysis capabilities
    to provide more sophisticated code modifications and recommendations.
    
    This agent combines the capabilities of:
    1. CodeAgent for code modifications
    2. CodebaseAnalyzer for advanced codebase analysis
    3. Custom tools for specialized operations
    """
    
    def __init__(
        self, 
        codebase: Codebase,
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        **kwargs
    ):
        """
        Initialize the enhanced coder agent.
        
        Args:
            codebase: The codebase to work with
            model_provider: The model provider to use
            model_name: The model name to use
            memory: Whether to enable conversation memory
            **kwargs: Additional arguments to pass to the CodeAgent
        """
        self.codebase = codebase
        self.model_provider = model_provider
        self.model_name = model_name
        self.memory = memory
        
        # Initialize the code agent
        self.code_agent = CodeAgent(
            codebase=codebase,
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            **kwargs
        )
        
        # Initialize the codebase analyzer
        self.analyzer = CodebaseAnalyzer(codebase)
        
        logger.info(f"EnhancedCoderAgent initialized with {model_provider}/{model_name}")
    
    def run(self, prompt: str) -> str:
        """
        Run the enhanced coder agent with a prompt.
        
        This method:
        1. Analyzes the prompt to determine if codebase analysis is needed
        2. Performs any necessary analysis
        3. Enhances the prompt with analysis results if relevant
        4. Runs the code agent with the enhanced prompt
        
        Args:
            prompt: The user prompt
            
        Returns:
            The agent's response
        """
        logger.info(f"Running EnhancedCoderAgent with prompt: {prompt[:100]}...")
        
        # Check if the prompt is requesting codebase analysis
        analysis_type = self._determine_analysis_type(prompt)
        
        if analysis_type:
            # Perform the requested analysis
            logger.info(f"Performing {analysis_type.value} analysis based on prompt")
            analysis_result = self.analyzer.analyze(analysis_type)
            
            # Enhance the prompt with analysis results
            enhanced_prompt = self._enhance_prompt_with_analysis(prompt, analysis_result)
            
            # Run the code agent with the enhanced prompt
            return self.code_agent.run(enhanced_prompt)
        else:
            # No analysis needed, run the code agent with the original prompt
            return self.code_agent.run(prompt)
    
    def _determine_analysis_type(self, prompt: str) -> Optional[AnalysisType]:
        """
        Determine if the prompt is requesting codebase analysis and which type.
        
        Args:
            prompt: The user prompt
            
        Returns:
            The analysis type to perform, or None if no analysis is needed
        """
        prompt_lower = prompt.lower()
        
        # Check for explicit analysis requests
        if "analyze dependencies" in prompt_lower or "dependency graph" in prompt_lower:
            return AnalysisType.DEPENDENCY_GRAPH
        elif "analyze components" in prompt_lower or "component interaction" in prompt_lower:
            return AnalysisType.COMPONENT_INTERACTION
        elif "technical debt" in prompt_lower:
            return AnalysisType.TECHNICAL_DEBT
        elif "cyclomatic complexity" in prompt_lower or "code complexity" in prompt_lower:
            return AnalysisType.CYCLOMATIC_COMPLEXITY
        elif "library optimization" in prompt_lower or "optimize libraries" in prompt_lower:
            return AnalysisType.LIBRARY_OPTIMIZATION
        elif "architecture patterns" in prompt_lower or "design patterns" in prompt_lower:
            return AnalysisType.ARCHITECTURE_PATTERNS
        elif "full analysis" in prompt_lower or "analyze codebase" in prompt_lower:
            return AnalysisType.FULL_ANALYSIS
        
        # Check for implicit analysis requests
        analysis_keywords = [
            "analyze", "analysis", "structure", "architecture", 
            "dependencies", "complexity", "quality", "patterns",
            "refactor", "improve", "optimize"
        ]
        
        if any(keyword in prompt_lower for keyword in analysis_keywords):
            # Implicit analysis request, perform a full analysis
            return AnalysisType.FULL_ANALYSIS
        
        return None
    
    def _enhance_prompt_with_analysis(self, prompt: str, analysis_result: AnalysisResult) -> str:
        """
        Enhance the prompt with analysis results.
        
        Args:
            prompt: The original prompt
            analysis_result: The analysis result
            
        Returns:
            The enhanced prompt
        """
        # Create a summary of the analysis
        analysis_summary = f"\n\n--- Codebase Analysis ({analysis_result.analysis_type.value}) ---\n"
        analysis_summary += f"{analysis_result.summary}\n\n"
        
        # Add key metrics
        if analysis_result.metrics:
            analysis_summary += "Key Metrics:\n"
            for key, value in analysis_result.metrics.items():
                if isinstance(value, dict):
                    continue  # Skip nested metrics
                analysis_summary += f"- {key}: {value}\n"
            analysis_summary += "\n"
        
        # Add recommendations
        if analysis_result.recommendations:
            analysis_summary += "Recommendations:\n"
            for rec in analysis_result.recommendations:
                analysis_summary += f"- {rec}\n"
            analysis_summary += "\n"
        
        # Combine the original prompt with the analysis summary
        enhanced_prompt = f"{prompt}\n\n{analysis_summary}\nPlease consider the above analysis in your response."
        
        return enhanced_prompt
    
    def analyze_codebase(self, analysis_type: Union[AnalysisType, str], force_refresh: bool = False) -> AnalysisResult:
        """
        Perform a specific type of codebase analysis.
        
        Args:
            analysis_type: The type of analysis to perform
            force_refresh: Whether to force a refresh of cached results
            
        Returns:
            The analysis result
        """
        return self.analyzer.analyze(analysis_type, force_refresh)
    
    def get_available_tools(self) -> List[str]:
        """
        Get a list of all available tools that can be used with the agent.
        
        Returns:
            List of tool names
        """
        # Standard code agent tools
        tools = [
            "view_file",
            "list_directory",
            "ripgrep_search",
            "create_file",
            "delete_file",
            "rename_file",
            "move_symbol",
            "reveal_symbol",
            "relace_edit",
            "replacement_edit",
            "global_replacement",
            "search_files_by_name",
            "reflection"
        ]
        
        # Analysis tools
        analysis_tools = [f"analyze_{t.value}" for t in AnalysisType]
        
        return tools + analysis_tools

# Example usage
if __name__ == "__main__":
    from codegen import Codebase
    
    # Initialize a codebase
    codebase = Codebase(repo="Zeeeepa/cod")
    
    # Create an enhanced coder agent
    agent = EnhancedCoderAgent(codebase)
    
    # Run the agent with a prompt
    response = agent.run("Analyze the structure of this codebase and suggest improvements")
    
    print(response)