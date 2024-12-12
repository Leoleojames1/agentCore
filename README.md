# agentCore
<p align="center">
  <img src="agentCore1.png" alt="agentCore logo" width="450"/>
</p>

This project provides files with methods to handle agentCores for agent_matrix.db

agentCore System:
1. Successfully initializes and stores your predefined agents in SQLite
2. Lists all available agent cores
3. Can mint new instances from any template
4. Properly handles loading and saving configurations

This gives you a solid foundation to:
1. Move the agent templates to separate JSON files later
2. Add more agent types easily
3. Track instances and templates in the database
4. Eventually add embedding functionality

The test shows everything working as intended:
- All predefined agents are loaded and stored
- Can create new instances with overrides (like the Minecraft agent with llama2)
- Loading and verification works
- Cleanup works

#TODO add pydantic agentCores
    
# installation
```bash
pip install agentCore
```

## Basic Usage

```python
from agentCore import agentCore
from ollama import chat

# Initialize agentCore
core = agentCore()

# Create basic Ollama agent configuration
basic_config = {
    "agent_id": "basic_assistant",
    "models": {
        "large_language_model": "llama2",
        "embedding_model": "nomic-embed-text"
    },
    "prompts": {
        "user_input_prompt": "You are a helpful assistant using local models.",
        "agentPrompts": {
            "llmSystemPrompt": "Focus on providing clear, accurate responses. Break down complex topics into understandable explanations.",
            "llmBoosterPrompt": "Include relevant examples when possible and highlight key points for better understanding."
        }
    },
    "commandFlags": {
        "STREAM_FLAG": True,
        "LOCAL_MODEL": True
    }
}

# Create the agent
agent = core.mintAgent(
    agent_id="basic_assistant",
    model_config=basic_config["models"],
    prompt_config=basic_config["prompts"],
    command_flags=basic_config["commandFlags"]
)

# Basic chat function
def chat_with_agent(agent_config, prompt):
    system_prompt = (
        f"{agent_config['agentCore']['prompts']['user_input_prompt']} "
        f"{agent_config['agentCore']['prompts']['agentPrompts']['llmSystemPrompt']} "
        f"{agent_config['agentCore']['prompts']['agentPrompts']['llmBoosterPrompt']}"
    )
    
    stream = chat(
        model=agent_config["agentCore"]["models"]["large_language_model"],
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        stream=True,
    )
    
    for chunk in stream:
        print(chunk['message']['content'], end='', flush=True)

# Example usage
chat_with_agent(agent, "Explain how neural networks work")
```

## Command-Line Creation

You can also create custom agents interactively using the command interface:


### Additional Database Management

```bash
# Create a new database
> /createDatabase research_results research_results.db

# Link database to existing agent
> /linkDatabase advanced_research_agent citations citations.db
```

# command-line interface
Start by using the /help command:
```cmd
Enter commands to manage agent cores. Type '/help' for options.
> /help
Commands:
  /agentCores - List all agent cores.
  /showAgent <agent_id> - Show agents with the specified ID.
  /createAgent <template_id> <new_agent_id> - Mint a new agent.
  /storeAgent <file_path> - Store agentCore from json path.
  /deleteAgent <uid> - Delete an agent by UID.
  /exportAgent <agent_id> - Export agentCore to json.
  /deleteAgent <uid> - Delete an agent by UID.
  /resetAgent <uid> - Reset an agent to the base template.
  /exit - Exit the interface.
```

Now to get the agentCores type:
```
> /agentCores

ID: default_agent, UID: ff22a0c1, Version: 1
ID: promptBase, UID: 6f18aba0, Version: 1
ID: speedChatAgent, UID: f1a7092c, Version: 1
ID: ehartfordDolphin, UID: 18556c0c, Version: 1
ID: minecraft_agent, UID: 25389031, Version: 1
ID: general_navigator_agent, UID: d1f12a46, Version: 1
```

Now to see an agent core use the following command
```cmd
> /showAgent general_navigator_agent
```

The agentCore will now be displayed:
```json
{
    "agentCore": {
        "agent_id": "general_navigator_agent",
        "version": 1,
        "uid": "d1f12a46",
        "save_state_date": "2024-12-11",
        "models": {
            "large_language_model": null,
            "embedding_model": null,
            "language_and_vision_model": null,
            "yolo_model": null,
            "whisper_model": null,
            "voice_model": null
        },
        "prompts": {
            "user_input_prompt": "",
            "agentPrompts": {
                "llmSystemPrompt": "You are a helpful llm assistant, designated with with fulling the user's request, the user is communicating with speech recognition and is sending their screenshot data to the vision model for decomposition. Receive this destription and Instruct the user and help them fullfill their request by collecting the vision data and responding. ",
                "llmBoosterPrompt": "Here is the output from the vision model describing the user screenshot data along with the users speech data. Please reformat this data, and formulate a fullfillment for the user request in a conversational speech manner which will be processes by the text to speech model for output. ",
                "visionSystemPrompt": "You are an image recognition assistant, the user is sending you a request and an image please fullfill the request. ",
                "visionBoosterPrompt": "Given the provided screenshot, please provide a list of objects in the image with the attributes that you can recognize. "
            }
        },
        "commandFlags": {
            "TTS_FLAG": false,
            "STT_FLAG": true,
            "CHUNK_FLAG": false,
            "AUTO_SPEECH_FLAG": false,
            "LLAVA_FLAG": true,
            "SPLICE_FLAG": false,
            "SCREEN_SHOT_FLAG": false,
            "LATEX_FLAG": false,
            "CMD_RUN_FLAG": false,
            "AGENT_FLAG": true,
            "MEMORY_CLEAR_FLAG": false
        },
        "conversation": {
            "save_name": "defaultConversation",
            "load_name": "defaultConversation"
        }
    }
}
```

Now to export an agentCore to json execute the following:
```cmd
> /exportAgent general_navigator_agent
Agent core saved to general_navigator_agent_core.json
```

# Advanced Usage
We can now construct advanced local assistants with ollama agentCores, and embedded db filenames, for nested knowledgeBase architectures.

```python
from agentCore import agentCore
from ollama import chat

# Initialize agentCore
core = agentCore()

# Create a coding assistant configuration
coding_config = {
    "agent_id": "coding_assistant",
    "models": {
        "large_language_model": "codellama",  # Using CodeLlama for coding tasks
        "embedding_model": "nomic-embed-text"  # For code embeddings and search
    },
    "prompts": {
        "user_input_prompt": "You are an expert programming assistant. Focus on writing clean, efficient, and well-documented code. Explain your implementation choices and suggest best practices.",
        "agentPrompts": {
            "llmSystemPrompt": "When analyzing code or programming problems, start by understanding the requirements, then break down the solution into logical steps. Include error handling and edge cases.",
            "llmBoosterPrompt": "Enhance your responses with: 1) Performance considerations 2) Common pitfalls to avoid 3) Testing strategies 4) Alternative approaches when relevant."
        }
    },
    "commandFlags": {
        "STREAM_FLAG": True,
        "LOCAL_MODEL": True,
        "CODE_MODE": True
    },
    "databases": {
        "conversation_history": "coding_assistant_chat.db",  # Dedicated chat history
        "python_knowledge": "pythonKnowledge.db",           # Python-specific knowledge
        "code_examples": "code_snippets.db"                 # Store useful code examples
    }
}

# Create the coding assistant
coding_agent = core.mintAgent(
    agent_id="coding_assistant",
    model_config=coding_config["models"],
    prompt_config=coding_config["prompts"],
    command_flags=coding_config["commandFlags"],
    db_config=coding_config["databases"]
)

# Stream chat function for code assistance
def stream_code_chat(agent_config, prompt):
    system_prompt = (
        f"{agent_config['agentCore']['prompts']['user_input_prompt']} "
        f"{agent_config['agentCore']['prompts']['agentPrompts']['llmSystemPrompt']} "
        f"{agent_config['agentCore']['prompts']['agentPrompts']['llmBoosterPrompt']}"
    )
    
    stream = chat(
        model=agent_config["agentCore"]["models"]["large_language_model"],
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        stream=True,
    )
    
    for chunk in stream:
        print(chunk['message']['content'], end='', flush=True)

# Usage examples
stream_code_chat(coding_agent, "Write a Python function to implement a binary search tree with insert and search methods")
```

Key changes made:
1. Changed to `coding_assistant` ID
2. Using `codellama` model
3. Added specialized coding-focused prompts
4. Created dedicated databases:
   - `coding_assistant_chat.db` for conversation history
   - `pythonKnowledge.db` for Python references
   - `code_snippets.db` for example storage
5. Added `CODE_MODE` flag
6. Updated prompts for programming focus

# AgentCore Database Configuration Guide

AgentCore provides flexible options for database configuration and customization. This guide covers all the ways you can customize your database setup.

## Basic Database Configuration

### Using base_path
Set a custom location for all databases:
```python
from agentCore import agentCore

# Put all databases in a custom location
core = agentCore(base_path="my/custom/path")
```

### Using Custom Database Paths
Override specific database paths:
```python
custom_paths = {
    "system": {
        "agent_matrix": "/path/to/my/matrix.db",
        "documentation": "/docs/store.db"
    },
    "agents": {
        "conversation": "/chats/{agent_id}.db"
    }
}

core = agentCore(db_config=custom_paths)
```

### Per-Agent Configuration
Specify custom paths when creating an agent:
```python
agent = core.mintAgent(
    agent_id="my_agent",
    db_config={
        "conversation": "/my/custom/chats/agent1.db",
        "knowledge": "/data/knowledge.db"
    }
)
```

## Template Configuration

### Using Base Template
Modify the base template:
```python
# Get base template first
core = agentCore()
base = core.getNewAgentCore()

# Modify the base template
base["agentCore"]["models"]["large_language_model"] = "my-custom-model"
base["agentCore"]["prompts"]["user_input_prompt"] = "My custom prompt"

# Create new core with modified template
custom_core = agentCore(template=base)
```

### Custom Template
Create a completely new template:
```python
custom_template = {
    "agentCore": {
        "agent_id": None,
        "version": 1,
        "models": {
            "large_language_model": "codellama",
            "my_custom_model": "custom-model"
        },
        "prompts": {
            "user_input_prompt": "Custom assistant prompt",
            "agentPrompts": {
                "llmSystemPrompt": "Custom system prompt",
                "llmBoosterPrompt": "Custom booster"
            }
        },
        "commandFlags": {
            "CUSTOM_FLAG": True,
            "AGENT_FLAG": True
        }
    }
}

# Initialize with custom template
custom_core = agentCore(template=custom_template)
```

### Template Structure Requirements
```python
{
    "agentCore": {
        "agent_id": None,  # Required but can be None initially
        "version": None,   # Optional, defaults to 1
        "models": {
            # At least one model should be defined
            "large_language_model": None
        },
        "prompts": {
            # At least need a user_input_prompt
            "user_input_prompt": "",
            "agentPrompts": {}
        },
        "commandFlags": {
            # AGENT_FLAG is required
            "AGENT_FLAG": True
        }
    }
}
```

### Sharing Templates
```python
# Save template to file
core.saveToFile("my_template", "template.json")

# Load template in another script
new_core = agentCore()
new_core.loadAgentFromFile("template.json")
```

## Custom Agent Matrix Configuration

### Direct Path Specification
```python
# Create agent matrix in custom location
core = agentCore(db_path="/my/custom/path/agent_matrix.db")
```

### Using Configuration Dictionary
```python
custom_config = {
    "system": {
        "agent_matrix": "/my/custom/path/agent_matrix.db"
    }
}

core = agentCore(db_config=custom_config)
```

### Multiple Project Matrices
```python
# Project A with its own matrix
project_a = agentCore(db_path="/project_a/agents.db")

# Project B with different matrix
project_b = agentCore(db_path="/project_b/agents.db")
```

### Environment-Based Configuration
Set environment variables:
```bash
export AGENTCORE_MATRIX_PATH="/custom/path/agent_matrix.db"
export AGENTCORE_BASE_PATH="/custom/path/agentcore_data"
```

### Team Configuration Sharing
```python
# team_config.py
TEAM_DB_CONFIG = {
    "system": {
        "agent_matrix": "/shared/team/agent_matrix.db",
        "documentation": "/shared/team/docs.db"
    }
}

# usage.py
from team_config import TEAM_DB_CONFIG
core = agentCore(db_config=TEAM_DB_CONFIG)
```