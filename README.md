# agentCores
<p align="center">
  <img src="https://raw.githubusercontent.com/Leoleojames1/agentCores/main/src/agentCores/data/agentCoresLogoFix.png" alt="agentCores logo" width="450"/>
</p>

## Overview

agentCores is a powerful MongoDB-based system for creating, managing, and deploying AI agents. It provides a comprehensive framework for handling complex agent configurations, making it easier to work with multiple AI models and agent types.

### What agentCores Does

1. **Agent Configuration Management**: 
   - Create, store, and manage AI agent configurations in MongoDB
   - Version control and unique identifiers for each agent
   - Template-based agent creation with extensive customization

2. **Database Integration**:
   - MongoDB collections for agent data, conversations, and knowledge
   - Customizable collection structures and configurations
   - Built-in database management and optimization

3. **Model and Prompt Management**:
   - Support for multiple AI models (language, vision, speech)
   - Structured prompt templates and version control
   - Integration with Ollama and other model providers

4. **Research and Development Tools**:
   - Built-in research assistant capabilities
   - Paper and code repository integration
   - Knowledge base management

5. **Command-line Interface**:
   - Interactive agent management
   - Real-time chat capabilities
   - Database administration tools

## Installation

```bash
pip install agentCores
```

### Dependencies
- Python 3.8+
- MongoDB
- ollama (optional, for LLM functionality)
- duckduckgo_search (optional, for research capabilities)

## MongoDB Structure

agentCores uses a single MongoDB database named `agentCores` with organized collections:

```
MongoDB Database: agentCores/
├── System Collections:
│   ├── agent_matrix         # Main agent configurations
│   ├── documentation        # System documentation
│   ├── templates           # Agent templates
│   └── template_files      # Template resources
├── Agent-Specific Collections:
│   ├── conversations_{agent_id}    # Chat history
│   ├── knowledge_{agent_id}        # Knowledge base
│   ├── embeddings_{agent_id}       # Vector embeddings
│   ├── research_{agent_id}         # Research data
│   └── design_patterns_{agent_id}  # Agent patterns
└── Shared Collections:
    ├── global_knowledge     # Shared knowledge base
    ├── model_configs       # Model configurations 
    └── prompt_templates    # Prompt templates
```

## Quick Start

### Basic Usage

```python
from agentCores import agentCores

# Initialize with default MongoDB connection
core = agentCores()

# Or specify custom MongoDB connection
core = agentCores(connection_uri="mongodb://localhost:27017/")

# Create a simple agent
agent = core.mintAgent(
    agent_id="my_assistant",
    model_config={
        "largeLanguageModel": {
            "names": ["llama2"],
            "instances": None,
            "concurrency": [],
            "parrallelModels": None
        }
    },
    prompt_config={
        "userInput": "You are a helpful assistant",
        "agent": {
            "llmSystem": "Provide clear and concise answers",
            "llmBooster": "Use examples when helpful"
        }
    }
)

# Start chatting
core.chat_with_agent("my_assistant")
```

### Research Assistant

```python
from agentCores import researchAssistant

# Initialize research assistant with MongoDB connection
assistant = researchAssistant(
    agent_id="research_agent", 
    connection_uri="mongodb://localhost:27017/"
)

# Process a research query
response = assistant.process_query("What is quantum computing?")

# Start interactive research session
assistant.start_chat()
```

## Core Features

### Agent Configuration Structure

```python
{
    "agentCore": {
        "identifyers": {
            "agent_id": str,          # Unique identifier
            "uid": str,               # Generated hash
            "version": int,           # Version number
            "creationDate": float,    # Creation timestamp
            "cpuNoiseHex": str        # Hardware identifier
        },
        "models": {
            "largeLanguageModel": {
                "names": list,         # Model names
                "instances": None,     # Instance count
                "concurrency": list,   # Concurrency settings
                "parrallelModels": None,
                "model_config_template": dict
            },
            "largeLanguageAndVisionAssistant": dict,
            "yoloVision": dict,
            "speechRecognitionSTT": dict,
            "voiceGenerationTTS": dict,
            "embedding": dict
        },
        "prompts": {
            "userInput": str,
            "agent": {
                "llmSystem": str,
                "llmBooster": str,
                "visionSystem": str,
                "visionBooster": str
            }
        },
        "modalityFlags": {
            "TTS_FLAG": bool,         # Text-to-speech
            "STT_FLAG": bool,         # Speech-to-text
            "CHUNK_AUDIO_FLAG": bool,
            "AUTO_SPEECH_FLAG": bool,
            "LLAVA_FLAG": bool,
            "SCREEN_SHOT_FLAG": bool,
            "SPLICE_VIDEO_FLAG": bool,
            "AUTO_COMMANDS_FLAG": bool,
            "CLEAR_MEMORY_FLAG": bool,
            "ACTIVE_AGENT_FLAG": bool
        },
        "evolutionarySettings": {
            "mutation": float,
            "pain": float,
            "hunger": float,
            "fasting": bool,
            "rationalizationFactor": float
        }
    }
}
```

### Command-line Interface

Start the interface:
```bash
python -m agentCores
```

Available commands:
```
/help                         Show available commands
/agentCores                   List all agent cores
/showAgent <agent_id>         Show agent configuration
/createAgent <template_id> <new_agent_id>   Create new agent
/createCustomAgent            Interactive agent creation
/createCollection <name>      Create MongoDB collection
/linkCollection <agent_id> <collection_name>  Link collection to agent
/storeAgent <file_path>       Import agent from JSON
/exportAgent <agent_id>       Export agent to JSON
/deleteAgent <agent_id>       Delete an agent
/resetAgent <agent_id>        Reset agent to base template
/chat <agent_id>             Start chat session
/knowledge <agent_id>         View knowledge base
/conversations <agent_id>     View conversation history
```

## Advanced Usage

### Custom Model Configuration

```python
model_config = {
    "largeLanguageModel": {
        "instances": 2,
        "names": ["llama2", "codellama"],
        "concurrency": ["parallel", "sequential"],
        "parrallelModels": True,
        "model_config_template": {
            "temperature": 0.7,
            "context_window": 4096,
            "streaming": True
        }
    }
}

agent = core.mintAgent(
    agent_id="advanced_agent",
    model_config=model_config
)
```

### Custom Collection Configuration

```python
# Create collection with indexes
core.create_collection_with_schema(
    "research_papers",
    indexes=[
        [("paper_id", 1)],
        [("title", "text")]
    ]
)

# Link collection to agent
core.linkDatabase(
    "research_agent",
    "research_papers"
)
```

### Research Integration

```python
from agentCores import researchAssistant

# Initialize with custom configuration
assistant = researchAssistant(
    agent_id="research_agent",
    connection_uri="mongodb://localhost:27017/"
)

# Create research collection
assistant.core.create_collection_with_schema(
    "papers",
    indexes=[
        [("paper_id", 1)],
        [("title", "text")]
    ]
)

# Process research queries
results = assistant.search("quantum computing")
response = assistant.process_query(
    "Explain recent advances in quantum computing"
)
```

## Development Tools

### Database Management

```python
# Create custom collection with indexes
core.create_collection_with_schema(
    "research_papers",
    indexes=[
        [("paper_id", 1)],
        [("title", "text")]
    ]
)

# Execute query
results = core.execute_query(
    "research_papers",
    {"title": {"$regex": "neural networks", "$options": "i"}}
)

# Bulk operations
core.bulk_insert(
    "research_papers",
    documents=[...]
)
```

### Template Management

```python
# Register template
template_id = core.register_template(
    "research_template",
    template_data={...},
    metadata={"version": "1.0"}
)

# Get template
template = core.get_template("research_template")

# List templates
templates = core.list_templates()
```

## Best Practices

1. **Database Management**
   - Use descriptive collection names
   - Implement proper MongoDB indexes
   - Regular maintenance of collections
   - Back up important data

2. **Agent Creation**
   - Start with templates
   - Version control configurations
   - Document custom settings
   - Test before deployment

3. **Error Handling**
   - Implement proper exception handling
   - Log errors and warnings
   - Include recovery strategies
   - Monitor agent performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow PEP 8 style guide
4. Add tests for new features
5. Update documentation
6. Submit pull request

## License

MIT License - see LICENSE file for details

## Author

Leo Borcherding

## Links

- GitHub: https://github.com/Leoleojames1/agentCores
- Documentation: https://agentcore.readthedocs.io/
- Issues: https://github.com/Leoleojames1/agentCores/issues

## Version

0.1.27 (2024-12-11)