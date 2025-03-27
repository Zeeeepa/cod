# Multi-Agent System for Code Development

This directory contains a powerful multi-agent system for code development that leverages the full range of codegen tools for code modification, analysis, and review.

## Components

### 1. Agent Creator (`agent_creator.py`)

The Agent Creator is a factory class that creates specialized code agents with different capabilities:

- **Coder**: Full-featured agent with all code modification tools
- **Reviewer**: Agent specialized for code review
- **Inspector**: Read-only agent for code inspection
- **Custom**: Agent with custom-selected tools

It provides a unified interface for creating agents with different tool sets, model providers, and configurations.

### 2. Multi-Agent System (`multi_agent_system.py`)

The Multi-Agent System combines specialized agents for different tasks, coordinated by a message orchestrator:

- **PR Reviewer Agent**: Reviews pull requests and provides feedback
- **Code Agent**: Modifies code based on requirements
- **Custom Agents**: Can be created with specific tool sets for specialized tasks

### 3. Message Orchestrator (from previous PR)

The Message Orchestrator manages conversation flows and context, enabling sophisticated multi-step interactions with users.

## Available Tools

The system provides access to all codegen tools:

- `view_file`: View the contents of a file
- `list_directory`: List the contents of a directory
- `ripgrep_search`: Search for patterns in the codebase
- `create_file`: Create a new file
- `delete_file`: Delete a file
- `rename_file`: Rename a file
- `move_symbol`: Move a symbol (function, class, etc.) to another file
- `reveal_symbol`: Find the definition of a symbol
- `relace_edit`: Edit a file using the Relace Instant Apply API
- `replacement_edit`: Replace text in a file using regex
- `global_replacement`: Replace text across the entire codebase
- `search_files_by_name`: Search for files by name
- `reflection`: Reflect on the current state and plan next steps

## Usage Examples

### Creating and Using Agents

```python
from agent_creator import AgentCreator, AgentType

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
```

### Using the Multi-Agent System

```python
from multi_agent_system import MultiAgentSystem

# Initialize the multi-agent system
system = MultiAgentSystem(repo_name="Zeeeepa/cod")

# Get available tools
tools = system.get_available_tools()
print(f"Available tools: {tools}")

# Analyze the codebase structure
analysis = system.analyze_codebase()
print(analysis)

# Review a PR
pr_review = system.review_pr(1)
print(pr_review)

# Modify code
modification = system.modify_code(
    "codegen-examples/examples/codegen_app/app.py",
    "Add error handling to the handle_mention function to catch and log any exceptions."
)
print(modification)

# Create a custom agent for code search
search_agent = system.create_custom_agent([
    "view_file", 
    "list_directory", 
    "ripgrep_search", 
    "search_files_by_name",
    "reflection"
])
```

## Integration with Slack

The system can be integrated with Slack using the Message Orchestrator from the previous PR. This enables:

1. **Conversation State Tracking**: Maintain state across multiple messages
2. **Context Persistence**: Keep track of the context of a conversation
3. **Multi-step Workflows**: Guide users through complex workflows step by step
4. **Agent Selection**: Dynamically select the appropriate agent based on the user's request

## Benefits

1. **Specialized Agents**: Each agent is optimized for a specific task
2. **Tool Flexibility**: Custom agents can be created with specific tool sets
3. **Model Selection**: Different models can be used for different tasks
4. **Conversation Management**: The Message Orchestrator manages complex conversations
5. **Code Modification**: Full access to code modification tools

## Getting Started

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up your environment variables in a `.env` file:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_SIGNING_SECRET=your_slack_signing_secret
   SLACK_NOTIFICATION_CHANNEL=your_slack_channel_id
   GITHUB_TOKEN=your_github_token
   ```

3. Run the example script:
   ```
   python multi_agent_system.py
   ```

## Architecture

The system follows a modular architecture:

1. **Agent Creator**: Factory for creating specialized agents
2. **Multi-Agent System**: Coordinates multiple agents for different tasks
3. **Message Orchestrator**: Manages conversation flows and context
4. **CodeAgent**: Executes code-related tasks using LLMs and tools

This architecture enables:
- Easy extension with new agent types
- Flexible tool configuration
- Dynamic agent selection based on task requirements
- Sophisticated conversation management

## Future Enhancements

1. **Agent Collaboration**: Enable agents to collaborate on complex tasks
2. **Learning from Feedback**: Improve agent performance based on user feedback
3. **Custom Tool Creation**: Allow users to create custom tools
4. **Workflow Automation**: Automate common development workflows
5. **Integration with CI/CD**: Integrate with CI/CD pipelines for automated code review and testing