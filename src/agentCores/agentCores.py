# agentCores.py
"""agentCores

A flexible framework for creating and managing AI agent configurations.

This package provides a comprehensive system for defining, storing, and managing
AI agent configurations. It supports custom templates, versioning, and persistent
storage of agent states and configurations.

Key Features:
1. Template-based agent creation with customization
2. SQLite-based persistent storage
3. Version control and unique identifiers for agents
4. Command-line interface for agent management
5. Support for custom database configurations
6. Flexible model and prompt management

Basic Usage:
    ```python
    from agentCores import agentCores
    
    # Create with default configuration
    agentCoresInstance = agentCores()
    
    # Create with custom database paths
    agentCoresInstance = agentCores(db_config={
        "agent_matrix": "custom_matrix.db",
        "conversation_history": "custom_conversations.db",
        "knowledge_base": "custom_knowledge.db"
    })
    
    # Create an agent with custom configuration
    agent = agentCoresInstance.mintAgent(
        agent_id="custom_agent",
        db_config={"conversation_history": "custom_agent_conv.db"},
        model_config={"largeLanguageModel": "gpt-4"},
        prompt_config={"userInput": "Custom prompt"}
    )
    ```

Advanced Usage:
    ```python
    # Create with custom template
    custom_template = {
        "agent_id": "specialized_agent",
        "models": {
            "largeLanguageModel": "llama",
            "custom_model": "specialized_model"
        },
        "custom_section": {
            "custom_param": "custom_value"
        }
    }
    
    agentCoresInstance = agentCores(template=custom_template)
    ```

Installation:
    pip install agentCores

Project Links:
    Homepage: https://github.com/Leoleojames1/agentCores
    Documentation: https://agentcore.readthedocs.io/ #NOT AVAILABLE
    Issues: https://github.com/Leoleojames1/agentCores/issues

Author: Leo Borcherding
Version: 0.1.0
Date: 2024-12-11
License: MIT
"""
# add uithub scrape, add arxiv
from pymongo import MongoClient
import json
import os
import time
import hashlib
import copy
from pathlib import Path
from typing import Optional, Dict, Any
from pkg_resources import resource_filename
from .agentMatrix import agentMatrix
from .databaseManager import databaseManager

class agentCores:
    
    #TODO ADD ENV VAR FOR agent_matrix.db path or allow users to make their own agent matrix structure with their own templates
    DEFAULT_DB_PATHS = {
        "system": {
            "agent_matrix": "agent_matrix",
            "documentation": "documentation",
            "templates": "templates",
            "template_files": "template_files"
        },
        "agents": {
            "conversation": "conversations_{agent_id}",
            "knowledge": "knowledge_{agent_id}",
            "designPatterns": "design_patterns_{agent_id}",
            "research_collection": "research_{agent_id}",
            "embeddings": "embeddings_{agent_id}"
        },
        "shared": {
            "global_knowledge": "global_knowledge",
            "models": "model_configs", 
            "prompts": "prompt_templates"
        }
    }
            
    def __init__(self, 
                 connection_uri: str = "mongodb://localhost:27017/",
                 custom_template: Optional[Dict] = None,
                 custom_db_paths: Optional[Dict] = None):
        """Initialize agentCores with optional custom template and database paths."""
        try:
            # Add time handling
            self.current_date = time.time()
            
            # MongoDB connection
            self.client = MongoClient(connection_uri, serverSelectionTimeoutMS=5000)
            self.client.server_info()
            self.db = self.client.agentCores
            
            # Use custom DB paths if provided, otherwise use defaults
            self.db_paths = custom_db_paths if custom_db_paths else self.DEFAULT_DB_PATHS
            
            # Initialize the base template
            self.base_template = self.initTemplate(custom_template)
            
            # Initialize database manager
            self.db_manager = databaseManager(connection_uri)
            
            # Initialize agentMatrix instance - this was missing
            self.agentMatrixObject = agentMatrix(connection_uri)
            
            # Initialize collections
            self._init_collections()
            
        except Exception as e:
            raise Exception(f"Failed to initialize MongoDB connection: {str(e)}")

    def _init_collections(self):
        """Initialize MongoDB collections based on configured paths."""
        # Create system collections
        for collection_name in self.db_paths["system"].values():
            self.db[collection_name].create_index("id", unique=True)
            
        # Create shared collections
        for collection_name in self.db_paths["shared"].values():
            self.db[collection_name].create_index("name", unique=True)
            
    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()
            
    def check_connection(self) -> bool:
        try:
            self.client.server_info()
            return True
        except Exception:
            return False
    
    def _init_db(self):
        """Initialize and optimize the database."""
        for category in self.db_paths:
            for db_path in self.db_paths[category].values():
                formatted_path = db_path.format(agent_id="shared")
                self.db_manager.optimize_database(formatted_path)

    def create_agent_databases(self, agent_id: str) -> Dict[str, str]:
        """Create agent-specific databases using configured paths."""
        collections = {}
        
        # Create collections using template paths
        for key, collection_template in self.db_paths["agents"].items():
            collection_name = collection_template.format(agent_id=agent_id)
            collection = self.db[collection_name]
            
            # Add indexes based on collection type
            if key == "conversation":
                collection.create_index([("session_id", 1)])
                collection.create_index([("save_name", 1)])
                collection.create_index([("timestamp", -1)])
                
            elif key == "knowledge":
                collection.create_index([("topic", 1)])
                collection.create_index([("content", "text")])
                collection.create_index([("last_updated", -1)])
                
            elif key == "embeddings":
                collection.create_index([("text_id", 1)], unique=True)
                collection.create_index([("last_used", -1)])
                
            elif key == "designPatterns":
                collection.create_index([("pattern_id", 1)])
                collection.create_index([("pattern_type", 1)])
                
            collections[key] = collection_name
            
        return collections

    def register_template(self, template_name: str, template_data: Dict, metadata: Dict = None) -> str:
        """Register a new template."""
        return self.agentMatrixObject.store_template(template_name, template_data, metadata)

    def register_custom_template(self, template_name: str, template_data: Dict) -> str:
        """Register a custom template for agent creation.
        
        Args:
            template_name: Name for the template
            template_data: Template configuration
            
        Returns:
            str: Template ID
        """
        # Validate template structure
        required_sections = ["identifyers", "models", "prompts", "modalityFlags"]
        for section in required_sections:
            if section not in template_data.get("agentCore", {}):
                raise ValueError(f"Template missing required section: {section}")
        
        # Generate template ID
        template_id = hashlib.sha256(
            json.dumps(template_data, sort_keys=True).encode()
        ).hexdigest()[:8]
        
        # Store template
        self.db[self.db_paths["system"]["templates"]].update_one(
            {"template_id": template_id},
            {
                "$set": {
                    "template_name": template_name,
                    "template_data": template_data,
                    "created_date": time.time()
                }
            },
            upsert=True
        )
        
        return template_id
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """Retrieve a template by name."""
        result = self.db[self.db_paths["system"]["templates"]].find_one(
            {"template_name": template_name}
        )
        return result["template_data"] if result else None

    def initTemplate(self, custom_template: Optional[Dict] = None) -> Dict:
        """Initialize or customize the agent template while maintaining required structure.
        
        This method sets up the base template for agent creation, optionally incorporating
        custom configurations while ensuring all required fields are present. The template
        defines the structure and default values for new agents.

        Args:
            custom_template (Optional[Dict]): Custom template configuration to merge with
                the base template. If provided, must follow the agentCore structure.

        Returns:
            Dict: The complete template configuration with all required fields.

        Examples:
            Basic template initialization:
            >>> core = agentCores()
            >>> template = core.initTemplate()

            Custom model configuration:
            >>> custom = {
            ...     "models": {
            ...         "largeLanguageModel": "llama2",
            ...         "embeddingModel": "nomic-embed-text"
            ...     }
            ... }
            >>> template = core.initTemplate(custom)

            Full custom configuration:
            >>> advanced = {
            ...     "agentCore": {
            ...         "models": {"largeLanguageModel": "codellama"},
            ...         "prompts": {
            ...             "userInput": "You are a code expert",
            ...             "agent": {
            ...                 "llmSystemPrompt": "Focus on code quality"
            ...             }
            ...         },
            ...         "modalityFlags": {"CODE_MODE": True}
            ...     }
            ... }
            >>> template = core.initTemplate(advanced)

        Notes:
            - All required fields are guaranteed to exist in the output
            - Custom templates are deeply merged with the base template
            - Invalid fields in custom templates are ignored
            - The template is used for all new agents created by mintAgent()
            - Updates to the template affect all future agent creations
        """
        # Define template structures
        template_version_info = {
            "version": None,
            "compatible_versions": None,
            "last_updated": None,
            "format_version": None  # e.g. "1.0.0" for template format itself
        }
        
        template_origin_info = {
            "source": None,  # "db_creation", "manual_import", "matrix_merge"
            "origin_date": None,  # When template entered the system
            "collection_date": None  # When template was added to matrix
        }
        
        identity_info = {
            "core_type": None,  # "db_native", "imported", "merged"
            "origin_info": {
                "source": None,
                "creation_date": None,
                "collection_date": None
            }
        }

        models_template = {
            "models": {
                "largeLanguageModel": {
                    "names" : [],
                    "instances": [],
                    "model_config_template": {}
                },
                "largeLanguageAndVisionAssistant": {
                    "names" : [],
                    "instances": [],
                    "model_config_template": {}
                },
                "yoloVision": {
                    "names" : [],
                    "instances": [],
                    "model_config_template": {}
                },
                "speechRecognitionSTT": {
                    "names" : [],
                    "instances": [],
                    "model_config_template": {}
                },
                "voiceGenerationTTS": {
                    "names" : [],
                    "instances": [],
                    "model_config_template": {}
                },
                "embedding" : {
                    "names" : [],
                    "instances": [],
                    "model_config_template": {}
                }
            }
        }

        model_config_template = {
            "model_config": {
                "concurrency" : None,
                "provider_config_template" : [],
                "concurrency" : [],
                "specialArgs": []
            },
        }
        
        provider_config_template = {
            "provider_config": {
                "org_id": None,
                "api_key": None,
                "api_base": None,
                "timeout": 30,
                "max_retries": 3
            },            
        }
        
        prompt_config_template = {
            "prompts": {
                "userInput": "",
                "agent": {
                    "llmSystem": None,
                    "llmBooster": None,
                    "visionSystem": None,
                    "visionBooster": None,
                    "primeDirective": None
                }
            }
        }
        
        core_database_config_template = {
            "databases": {
                "agent_matrix": "agent_matrix.db",
                "conversation_history": "{agent_id}_conversation.db",
                "knowledge_base": "knowledge_base.db",
                "research_collection": "research_collection.db",
                "template_files": "template_files.db"
            }
        }
        
        flags_config_template = {
            "modalityFlags": {
                "TTS_FLAG": False,
                "STT_FLAG": False,
                "CHUNK_AUDIO_FLAG": False,
                "AUTO_SPEECH_FLAG": False,
                "LLAVA_FLAG": False,
                "SCREEN_SHOT_FLAG": False,
                "SPLICE_VIDEO_FLAG": False,
                "AUTO_COMMANDS_FLAG": False,
                "CLEAR_MEMORY_FLAG": False,
                "ACTIVE_AGENT_FLAG": True,
            }
        }
        
        evolution_config_template = {
            "evolutionarySettings": {
                "mutation": None,
                "pain": None,
                "hunger" : None,
                "fasting" : None,
                "rationalizationFactor" : None,  
            }
        }
        
        special_config_template = {
            "specialArgs": {
                "blocks": None,
                "tokens": None,
                "layers": None,
                "temperature": 0.7,  # Add temperature
                "context_window": 4096,  # Add context window
                "streaming": True,  # Add streaming option
                "top_p": 1.0,  # Add sampling parameter
                "top_k": 40,  # Add top-k sampling
                "stop_sequences": [],  # Add stop sequences
                "max_tokens": None,  # Add max tokens
                "presence_penalty": 0.0,  # Add presence penalty
                "frequency_penalty": 0.0  # Add frequency penalty
            }
        }
        
        # Now create the base template using the defined templates
        base_template = {
            "agentCore": {
                "identifyers": {
                    "agent_id": None,
                    "uid": None,
                    "template_version_info": template_version_info,
                    "creationDate": None,
                    "cpuNoiseHex": None,
                    "identity_info": identity_info
                },
                "metaData": {
                    "models_template": None,
                    "prompt_config_template": None,
                    "core_database_config_template": None,
                    "flags_config_template": None,
                    "evolution_config_template": None,
                    "special_config_template": None
                },
                **models_template,
                **prompt_config_template,
                **core_database_config_template,
                **flags_config_template,
                **evolution_config_template,
                **special_config_template
            }
        }
        
        # Handle custom template merging
        if custom_template:
            def deep_merge(base: Dict, custom: Dict) -> Dict:
                for key, value in custom.items():
                    if isinstance(base.get(key), dict) and isinstance(value, dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base
            
            if "agentCore" not in custom_template:
                custom_template = {"agentCore": custom_template}
            
            deep_merge(base_template["agentCore"], custom_template["agentCore"])
        
        self.base_template = base_template
        self.agentCores = json.loads(json.dumps(base_template))
        return base_template

    def getNewAgentCore(self) -> Dict:
        """Get a fresh agent core based on the base template."""
        return json.loads(json.dumps(self.base_template))  # Deep copy
        
    def _createAgentConfig(self, agent_id: str, config: Dict) -> Dict:
        """Create a full agent configuration from base template and config data."""
        new_core = self.getNewAgentCore()
        new_core["agentCore"]["identifyers"]["agent_id"] = agent_id  # Changed from agentCore.agent_id
        new_core["agentCore"]["identifyers"]["dateOfSaveState"] = self.current_date  # Changed from agentCore.dateOfSaveState
        
        # Update prompts - changed field names to match new structure
        if "llmSystem" in config:
            new_core["agentCore"]["prompts"]["agent"]["llmSystem"] = config["llmSystem"]
        if "llmBooster" in config:
            new_core["agentCore"]["prompts"]["agent"]["llmBooster"] = config["llmBooster"]
        if "visionSystem" in config:
            new_core["agentCore"]["prompts"]["agent"]["visionSystem"] = config["visionSystem"]
        if "visionBooster" in config:
            new_core["agentCore"]["prompts"]["agent"]["visionBooster"] = config["visionBooster"]
                
        # Update command flags
        if "modalityFlags" in config:
            new_core["agentCore"]["modalityFlags"].update(config["modalityFlags"])
                
        return new_core

    def storeAgentCore(self, agent_id: str, core_config: Dict[str, Any]) -> None:
        """Store an agent configuration in the matrix."""
        # Let agentMatrix handle serialization
        self.agentMatrixObject.upsert(
            documents=[core_config],  # Pass the raw dict
            ids=[agent_id],
            metadatas=[{"agent_id": agent_id, "save_date": self.current_date}]
        )

    def loadAgentCore(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load an agent configuration from the library."""
        results = self.agentMatrixObject.get(ids=[agent_id])
        if results and results["documents"]:
            config = results["documents"][0]  # Already deserialized by agentMatrix
            self.agentCores = config
            return config
        return None

    def listAgentCores(self) -> list:
        """List all available agent cores in the system.
        
        Retrieves a list of all agents stored in the system, including their
        IDs, UIDs, and version numbers. This is useful for managing multiple
        agents and checking their current states.

        Returns:
            list: List of dictionaries containing agent information:
                - agent_id: The unique identifier of the agent
                - uid: The unique hash of the agent's configuration
                - version: The current version number of the agent

        Examples:
            List all agents:
            >>> core = agentCores()
            >>> agents = core.listAgentCores()
            >>> for agent in agents:
            ...     print(f"ID: {agent['agent_id']}, Version: {agent['version']}")

            Find specific agent versions:
            >>> agents = core.listAgentCores()
            >>> research_agents = [a for a in agents if "research" in a['agent_id']]
            >>> for agent in research_agents:
            ...     print(f"{agent['agent_id']}: v{agent['version']}")

        Notes:
            - Returns an empty list if no agents are found
            - UIDs and versions are marked as "Unknown" if not set
            - Useful for system management and agent inventory
        """
        all_agents = self.agentMatrixObject.get()
        agent_cores = []
        for metadata, document in zip(all_agents["metadatas"], all_agents["documents"]):
            agent_core = json.loads(document)  # Deserialize the JSON string into a dictionary
            agent_cores.append({
                "agent_id": metadata["agent_id"],
                "uid": agent_core["agentCore"].get("uid", "Unknown"),
                "version": agent_core["agentCore"].get("version", "Unknown"),
            })
        return agent_cores
    
    def list_templates(self) -> list:
        """List all available templates."""
        templates = self.db[self.db_paths["system"]["templates"]].find()
        return [{
            "name": t["template_name"],
            "id": t["template_id"],
            "created_date": t["created_date"]
        } for t in templates]
        
    def _generateUID(self, core_config: Dict) -> str:
        """Generate a unique identifier (UID) based on the agent core configuration."""
        core_json = json.dumps(core_config, sort_keys=True)
        return hashlib.sha256(core_json.encode()).hexdigest()[:8]
    
    def mintAgent(self,
                agent_id: str,
                db_config: Optional[Dict] = None,
                model_config: Optional[Dict] = None,
                prompt_config: Optional[Dict] = None,
                command_flags: Optional[Dict] = None) -> Dict:
        """Create a new agent with proper database initialization and configuration.
        
        This method creates a new AI agent with a complete configuration, including databases,
        models, prompts, and command flags. It handles all necessary initialization steps
        and ensures proper storage setup.

        Args:
            agent_id (str): Unique identifier for the new agent. Used for database paths
                and configuration management.
            db_config (Optional[Dict]): Custom database configuration for the agent.
                Can override default paths and add new databases. Format:
                {
                    "custom_db": "path/to/db.db",
                    "knowledge_base": "custom/path/kb.db"
                }
            model_config (Optional[Dict]): Model configurations for the agent.
                Specifies which AI models to use. Format:
                {
                    "largeLanguageModel": "llama2",
                    "embeddingModel": "nomic-embed-text"
                }
            prompt_config (Optional[Dict]): Prompt configurations for the agent.
                Defines system and user prompts. Format:
                {
                    "userInput": "Custom prompt",
                    "agent": {
                        "llmSystem": "System instruction",
                        "llmBooster": "Additional context"
                    }
                }
            command_flags (Optional[Dict]): Command flags for the agent.
                Controls agent behavior and features. Format:
                {
                    "STREAM_FLAG": True,
                    "LOCAL_MODEL": True
                }

        Returns:
            Dict: Complete agent configuration including:
                - Generated UID
                - Database paths
                - Model configurations
                - Prompt settings
                - Command flags
                - Version information

        Examples:
            Basic usage with default settings:
            >>> core = agentCores()
            >>> agent = core.mintAgent("basic_agent")

            Custom configuration with specific model and prompts:
            >>> agent = core.mintAgent(
            ...     agent_id="custom_assistant",
            ...     model_config={"largeLanguageModel": "llama2"},
            ...     prompt_config={
            ...         "userInput": "You are a helpful assistant",
            ...         "agent": {"llmSystem": "Be concise and clear"}
            ...     }
            ... )

            Advanced usage with custom databases and flags:
            >>> agent = core.mintAgent(
            ...     agent_id="research_agent",
            ...     db_config={
            ...         "papers_db": "research/papers.db",
            ...         "citations_db": "research/citations.db"
            ...     },
            ...     command_flags={"RESEARCH_MODE": True}
            ... )

        Notes:
            - All database paths are automatically created if they don't exist
            - Default databases (conversation, knowledge, embeddings) are always initialized
            - The agent's configuration is automatically stored in the agent matrix
            - A unique identifier (UID) is generated based on the configuration
            - The agent starts at version 1 and increments with updates
        """
        # Create agent-specific databases
        agent_db_paths = self.create_agent_databases(agent_id)
        
        # Merge with any custom db_config
        if db_config:
            agent_db_paths.update(db_config)
        
        # Create agent configuration
        new_config = self.getNewAgentCore()
        
        # Set identifiers
        new_config["agentCore"]["identifyers"]["agent_id"] = agent_id
        new_config["agentCore"]["identifyers"]["dateOfSaveState"] = self.current_date
        new_config["agentCore"]["identifyers"]["version"] = 1
        new_config["agentCore"]["databases"] = agent_db_paths
        
        # Handle model configuration
        if model_config:
            for model_type, value in model_config.items():
                if isinstance(value, str):
                    # Convert string value to new model structure
                    new_config["agentCore"]["models"][model_type] = {
                        "instances": None,
                        "names": [value],
                        "concurrency": [],
                        "parrallelModels": None,
                        "specialArgs": {
                            "blocks": None,
                            "tokens": None,
                            "layers": None
                        }
                    }
                elif isinstance(value, dict):
                    # If a complete model config is provided, use it
                    new_config["agentCore"]["models"][model_type].update(value)
        
        # Handle prompt configuration
        if prompt_config:
            if "userInput" in prompt_config:
                new_config["agentCore"]["prompts"]["userInput"] = prompt_config["userInput"]
            if "agent" in prompt_config:
                agent_prompts = prompt_config["agent"]
                if "llmSystem" in agent_prompts:
                    new_config["agentCore"]["prompts"]["agent"]["llmSystem"] = agent_prompts["llmSystem"]
                if "llmBooster" in agent_prompts:
                    new_config["agentCore"]["prompts"]["agent"]["llmBooster"] = agent_prompts["llmBooster"]
                if "visionSystem" in agent_prompts:
                    new_config["agentCore"]["prompts"]["agent"]["visionSystem"] = agent_prompts["visionSystem"]
                if "visionBooster" in agent_prompts:
                    new_config["agentCore"]["prompts"]["agent"]["visionBooster"] = agent_prompts["visionBooster"]
        
        # Update command flags
        if command_flags:
            new_config["agentCore"]["modalityFlags"].update(command_flags)
        
        # Generate UID
        new_config["agentCore"]["identifyers"]["uid"] = self._generateUID(new_config)
        
        # Store the new agent
        self.storeAgentCore(agent_id, new_config)
        return new_config

    def resetAgentCore(self):
        """Reset the current agent core to base template state."""
        self.agentCores = self.getNewAgentCore()
        return self.agentCores

    def getCurrentCore(self) -> Dict:
        """Get the current agent core configuration."""
        return self.agentCores

    def updateCurrentCore(self, updates: Dict):
        """Update the current agent core with new values."""
        self._mergeConfig(self.agentCore["agentCore"], updates)
        self.agentCores["agentCore"]["version"] += 1
        self.agentCores["agentCore"]["uid"] = self._generateUID(self.agentCores)
        
    def _mergeConfig(self, base: Dict, updates: Dict):
        """Recursively merge configuration updates."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._mergeConfig(base[key], value)
            else:
                base[key] = value

    def deleteAgentCore(self, agent_id: str) -> None:
        """Remove an agent configuration from storage."""
        self.agentMatrixObject.delete(ids=[agent_id])

    def saveToFile(self, agent_id: str, file_path: str) -> None:
        """Save an agent configuration to a JSON file.
        
        Exports an agent's complete configuration to a JSON file for backup,
        sharing, or version control purposes. The file includes all settings,
        prompts, model configurations, and database paths.

        Args:
            agent_id (str): The ID of the agent to export.
            file_path (str): Where to save the JSON file. If the file exists,
                it will be overwritten.

        Examples:
            Export a single agent:
            >>> core = agentCores()
            >>> core.saveToFile("my_assistant", "assistant_backup.json")

            Export with custom path:
            >>> core.saveToFile(
            ...     "research_agent", 
            ...     "backups/research/agent_v1.json"
            ... )

        Notes:
            - Creates parent directories if they don't exist
            - Overwrites existing files without warning
            - The JSON file is human-readable with proper indentation
            - Can be used with loadAgentFromFile to restore configurations
        """
        config = self.loadAgentCore(agent_id)
        if config:
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=4)

    def loadAgentFromFile(self, file_path: str) -> None:
        """Load an agent configuration from a JSON file and store in matrix."""
        with open(file_path, 'r') as f:
            config = json.load(f)
            if "agentCore" in config and "agent_id" in config["agentCore"]:
                self.storeAgentCore(config["agentCore"]["agent_id"], config)
            else:
                raise ValueError("Invalid agent configuration file")

    def migrateAgentCores(self):
        """Migrate and consolidate agent cores from old template to new template structure."""
        print("Migrating and consolidating agent cores...")
        
        # Get all agents from both collections
        try:
            agent_cores = list(self.db.agent_cores.find())
            matrix_cores = list(self.db.agent_matrix_agent_cores.find())
            
            print(f"Found {len(agent_cores)} agents in agent_cores")
            print(f"Found {len(matrix_cores)} agents in agent_matrix_agent_cores")
            
            # Consolidate all agents
            all_agents = []
            seen_agent_ids = set()
            
            # Process matrix cores first (they're in the correct collection)
            for agent in matrix_cores:
                agent_id = agent.get('agent_id')
                if agent_id and agent_id not in seen_agent_ids:
                    all_agents.append(agent)
                    seen_agent_ids.add(agent_id)
                    
            # Add agents from agent_cores if they don't exist in matrix
            for agent in agent_cores:
                agent_id = agent.get('agent_id')
                if agent_id and agent_id not in seen_agent_ids:
                    # Move to matrix collection format
                    all_agents.append(agent)
                    seen_agent_ids.add(agent_id)
            
            print(f"\nMigrating {len(all_agents)} total unique agents...")
            
            # Process each agent
            for old_agent in all_agents:
                try:
                    agent_id = old_agent.get('agent_id', 'Unknown')
                    print(f"\nMigrating agent: {agent_id}")
                    
                    # Parse the core data
                    if isinstance(old_agent.get('core_data'), str):
                        core_data = json.loads(old_agent['core_data'])
                    else:
                        core_data = old_agent.get('core_data', {})
                    
                    # Create new agent core from template
                    new_agent = self.getNewAgentCore()
                    old_core = core_data.get("agentCore", {})
                    
                    # Migrate identifiers
                    new_agent["agentCore"]["identifyers"]["agent_id"] = agent_id
                    new_agent["agentCore"]["identifyers"]["version"] = old_core.get("version", 1)
                    new_agent["agentCore"]["identifyers"]["dateOfSaveState"] = old_core.get("save_state_date")
                    new_agent["agentCore"]["identifyers"]["uid"] = old_core.get("uid")
                    
                    # Migrate models with new structure
                    model_mapping = {
                        "large_language_model": "largeLanguageModel",
                        "embedding_model": "embedding",
                        "language_and_vision_model": "largeLanguageAndVisionAssistant",
                        "yolo_model": "yoloVision",
                        "whisper_model": "speechRecognitionSTT",
                        "voice_model": "voiceGenerationTTS"
                    }
                    
                    old_models = old_core.get("models", {})
                    for old_name, new_name in model_mapping.items():
                        model_value = old_models.get(old_name)
                        if model_value is not None:
                            new_agent["agentCore"]["models"][new_name] = {
                                "names": [model_value] if model_value else [],
                                "instances": None,
                                "concurrency": [],
                                "model_config_template": {}
                            }
                    
                    # Migrate prompts
                    old_prompts = old_core.get("prompts", {})
                    new_agent["agentCore"]["prompts"]["userInput"] = old_prompts.get("user_input_prompt", "")
                    
                    if "agentPrompts" in old_prompts:
                        old_agent_prompts = old_prompts["agentPrompts"]
                        new_agent["agentCore"]["prompts"]["agent"] = {
                            "llmSystem": old_agent_prompts.get("llmSystemPrompt"),
                            "llmBooster": old_agent_prompts.get("llmBoosterPrompt"),
                            "visionSystem": old_agent_prompts.get("visionSystemPrompt"),
                            "visionBooster": old_agent_prompts.get("visionBoosterPrompt")
                        }
                    
                    # Migrate command flags
                    old_flags = old_core.get("commandFlags", {})
                    flag_mapping = {
                        "TTS_FLAG": "TTS_FLAG",
                        "STT_FLAG": "STT_FLAG",
                        "CHUNK_FLAG": "CHUNK_AUDIO_FLAG",
                        "AUTO_SPEECH_FLAG": "AUTO_SPEECH_FLAG",
                        "LLAVA_FLAG": "LLAVA_FLAG",
                        "SPLICE_FLAG": "SPLICE_VIDEO_FLAG",
                        "SCREEN_SHOT_FLAG": "SCREEN_SHOT_FLAG",
                        "CMD_RUN_FLAG": "AUTO_COMMANDS_FLAG",
                        "AGENT_FLAG": "ACTIVE_AGENT_FLAG",
                        "MEMORY_CLEAR_FLAG": "CLEAR_MEMORY_FLAG"
                    }
                    
                    for old_flag, new_flag in flag_mapping.items():
                        if old_flag in old_flags:
                            new_agent["agentCore"]["modalityFlags"][new_flag] = old_flags[old_flag]
                    
                    # Set up associated collection references
                    new_agent["agentCore"]["databases"] = {
                        "conversation": f"conversations_{agent_id}",
                        "knowledge": f"knowledge_{agent_id}",
                        "designPatterns": f"design_patterns_{agent_id}",
                        "research": f"research_{agent_id}",
                        "embeddings": f"embeddings_{agent_id}"
                    }
                    
                    # Generate new UID
                    new_agent["agentCore"]["identifyers"]["uid"] = self._generateUID(new_agent)
                    
                    # Store in agent_matrix_agent_cores
                    self.storeAgentCore(agent_id, new_agent)
                    print(f"Successfully migrated agent: {agent_id}")
                    
                except Exception as e:
                    print(f"Error migrating agent {agent_id}: {str(e)}")
                    continue
            
            # Clean up: remove old collection if migration successful
            if self.db.agent_cores.count_documents({}) > 0:
                print("\nRemoving old agent_cores collection...")
                self.db.agent_cores.drop()
            
            print("\nMigration and consolidation complete.")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            raise
 
    def linkDatabase(self, agent_id: str, collection_name: str, new_collection_name: str) -> None:
        """Link a collection to an existing agent."""
        agent = self.loadAgentCore(agent_id)
        if agent:
            agent["agentCore"]["databases"][collection_name] = new_collection_name
            self.storeAgentCore(agent_id, agent)
            print(f"Linked collection '{new_collection_name}' to agent '{agent_id}'")
        else:
            print(f"Agent '{agent_id}' not found")
        
    def importAgentCores(self, connection_uri: str) -> None:
        """
        Import agent cores from another MongoDB instance into the current system.
        
        Args:
            connection_uri (str): MongoDB connection URI for the source database
                e.g. "mongodb://hostname:27017/", "mongodb+srv://user:pass@cluster.domain/"
                
        Raises:
            Exception: If there's an error connecting or during import
        """
        print(f"Importing agent cores from: {connection_uri}")
        
        try:
            # Create a temporary connection to the source database
            source_client = MongoClient(connection_uri)
            source_db = source_client.agentCores
            
            # Get all agents from the source database
            source_agents = source_db.agent_cores.find()
            import_count = 0
            
            # Import each agent
            for agent in source_agents:
                try:
                    agent_id = agent.get('agent_id')
                    if not agent_id:
                        print("Warning: Skipping agent with missing ID")
                        continue
                    
                    # Check if agent exists in current system
                    existing = self.agent_cores.find_one({"agent_id": agent_id})
                    
                    if existing:
                        # Update existing agent if source is newer
                        if agent.get('last_updated', 0) > existing.get('last_updated', 0):
                            self.agent_cores.update_one(
                                {"agent_id": agent_id},
                                {
                                    "$set": {
                                        "core_data": agent['core_data'],
                                        "save_date": agent.get('save_date'),
                                        "last_updated": time.time()
                                    }
                                }
                            )
                            print(f"Updated agent: {agent_id}")
                        else:
                            print(f"Skipped agent (not newer): {agent_id}")
                    else:
                        # Insert new agent
                        self.agent_cores.insert_one({
                            "agent_id": agent_id,
                            "core_data": agent['core_data'],
                            "save_date": agent.get('save_date'),
                            "last_updated": time.time()
                        })
                        print(f"Imported new agent: {agent_id}")
                    
                    import_count += 1
                    
                    # Import associated collections if they exist
                    collection_prefixes = [
                        f"conversations_{agent_id}",
                        f"knowledge_{agent_id}",
                        f"design_patterns_{agent_id}",
                        f"research_{agent_id}",
                        f"embeddings_{agent_id}"
                    ]
                    
                    for prefix in collection_prefixes:
                        if prefix in source_db.list_collection_names():
                            # Copy collection data
                            source_data = list(source_db[prefix].find())
                            if source_data:
                                self.db[prefix].insert_many(source_data)
                                print(f"Imported {len(source_data)} documents for {prefix}")
                    
                except Exception as e:
                    print(f"Warning: Error importing agent {agent_id}: {str(e)}")
                    continue
                    
            print(f"\nImport complete. Processed {import_count} agents.")
            
        except Exception as e:
            raise Exception(f"Error importing agent cores: {str(e)}")
            
        finally:
            # Close the temporary connection
            if 'source_client' in locals():
                source_client.close()
        
    def commandInterface(self):
        """Command-line interface for managing agents."""
        
        print("Enter commands to manage agent cores. Type '/help' for options.")
        
        while True:
            command = input("> ").strip()
            if command == "/help":
                print("Commands:")
                print("  /agentCores - List all agent cores")
                print("  /showAgent <agent_id> - Show agent configuration")
                print("  /createAgent <template_id> <new_agent_id> - Create new agent")
                print("  /createCustomAgent - Interactive agent creation")
                print("  /createCollection <name> - Create MongoDB collection")
                print("  /linkCollection <agent_id> <collection_name> - Link collection to agent")
                print("  /storeAgent <file_path> - Import agent from JSON")
                print("  /exportAgent <agent_id> - Export agent to JSON")
                print("  /deleteAgent <agent_id> - Delete an agent")
                print("  /resetAgent <agent_id> - Reset agent to base template")
                print("  /chat <agent_id> - Start chat session")
                print("  /knowledge <agent_id> - View knowledge base")
                print("  /conversations <agent_id> - View conversation history") 
                print("  /importAgents <uri> - Import agents from another MongoDB")
                print("  /exportKnowledge <agent_id> <file_path> - Export knowledge")
                print("  /importKnowledge <agent_id> <file_path> - Import knowledge")
                print("  /exit - Exit interface")
                
            elif command == "/agentCores":
                agents = self.listAgentCores()
                for agent in agents:
                    print(f"ID: {agent['agent_id']}, UID: {agent['uid']}, Version: {agent['version']}")
                    
            elif command.startswith("/showAgent"):
                try:
                    _, agent_id = command.split()
                    agent = self.loadAgentCore(agent_id)
                    if agent:
                        print(json.dumps(agent, indent=4))
                    else:
                        print(f"No agent found with ID: {agent_id}")
                except ValueError:
                    print("Usage: /showAgent <agent_id>")
                    
            elif command.startswith("/createAgent"):
                try:
                    _, template_name, new_agent_id = command.split()
                    template = self.get_template(template_name)
                    if not template:
                        print(f"Template '{template_name}' not found")
                        continue
                        
                    agent = self.mintAgent(new_agent_id, template=template)
                    print(f"Created agent: {new_agent_id}")
                except ValueError:
                    print("Usage: /createAgent <template_name> <new_agent_id>")

            elif command == "/createCustomAgent":
                try:
                    print("\nInteractive Custom Agent Creation")
                    agent_id = input("Enter agent ID: ")
                    
                    # Model configuration
                    model_config = {}
                    print("\nModel Configuration (press Enter to skip):")
                    llm = input("Large Language Model: ")
                    if llm: 
                        model_config["largeLanguageModel"] = {
                            "names": [llm],
                            "instances": None,
                            "concurrency": []
                        }
                    
                    vision = input("Vision Model: ")
                    if vision:
                        model_config["largeLanguageAndVisionAssistant"] = {
                            "names": [vision],
                            "instances": None,
                            "concurrency": []
                        }
                    
                    # Prompt configuration
                    prompt_config = {"agent": {}}
                    print("\nPrompt Configuration:")
                    system_prompt = input("System Prompt: ")
                    if system_prompt:
                        prompt_config["agent"]["llmSystem"] = system_prompt
                    
                    # Collection configuration  
                    collection_config = {}
                    print("\nCollection Configuration:")
                    while True:
                        collection_name = input("\nEnter collection name (or Enter to finish): ")
                        if not collection_name: break
                        
                        indexes = []
                        while True:
                            index_field = input("Add index field (or Enter to finish): ")
                            if not index_field: break
                            index_type = input("Index type (1=ascending, -1=descending, text=text): ")
                            if index_type == "text":
                                indexes.append([(index_field, "text")])
                            else:
                                indexes.append([(index_field, int(index_type))])
                        
                        collection = self.createCollection(collection_name, indexes)
                        collection_config[collection_name] = collection.name
                        print(f"Created collection: {collection_name}")
                    
                    # Create the agent
                    agent = self.mintAgent(
                        agent_id=agent_id,
                        model_config=model_config,
                        prompt_config=prompt_config,
                        db_config=collection_config
                    )
                    print(f"\nCreated custom agent: {agent_id}")
                    
                except Exception as e:
                    print(f"Error creating custom agent: {e}")
                    
            elif command.startswith("/createCollection"):
                try:
                    _, collection_name = command.split()
                    self.createCollection(collection_name)
                    print(f"Created collection: {collection_name}")
                except ValueError:
                    print("Usage: /createCollection <name>")
                    
            elif command.startswith("/linkCollection"):
                try:
                    _, agent_id, collection_name = command.split()
                    self.linkDatabase(agent_id, collection_name)
                    print(f"Linked collection to agent: {agent_id}")
                except ValueError:
                    print("Usage: /linkCollection <agent_id> <collection_name>")

            elif command.startswith("/storeAgent"):
                try:
                    _, file_path = command.split()
                    with open(file_path) as f:
                        agent_data = json.load(f)
                    
                    if "agentCore" not in agent_data:
                        print("Invalid agent data: Missing agentCore")
                        continue
                        
                    agent_id = agent_data["agentCore"].get("agent_id")
                    if not agent_id:
                        print("Invalid agent data: Missing agent_id")
                        continue
                    
                    self.storeAgentCore(agent_id, agent_data)
                    print(f"Stored agent: {agent_id}")
                    
                except FileNotFoundError:
                    print(f"File not found: {file_path}")
                except json.JSONDecodeError:
                    print("Invalid JSON in file")
                except ValueError:
                    print("Usage: /storeAgent <file_path>")

            elif command.startswith("/exportAgent"):
                try:
                    _, agent_id = command.split()
                    agent = self.loadAgentCore(agent_id)
                    if agent:
                        file_path = f"{agent_id}_core.json"
                        with open(file_path, "w") as f:
                            json.dump(agent, f, indent=4)
                        print(f"Exported agent to: {file_path}")
                    else:
                        print(f"Agent not found: {agent_id}")
                except ValueError:
                    print("Usage: /exportAgent <agent_id>")
                    
            elif command.startswith("/deleteAgent"):
                try:
                    _, agent_id = command.split()
                    self.deleteAgentCore(agent_id)
                    print(f"Deleted agent: {agent_id}")
                except ValueError:
                    print("Usage: /deleteAgent <agent_id>")
                    
            elif command.startswith("/resetAgent"):
                try:
                    _, agent_id = command.split()
                    agent = self.loadAgentCore(agent_id)
                    if agent:
                        self.resetAgentCore()
                        print(f"Reset agent: {agent_id}")
                    else:
                        print(f"Agent not found: {agent_id}")
                except ValueError:
                    print("Usage: /resetAgent <agent_id>")
                    
            elif command.startswith("/chat"):
                try:
                    _, agent_id = command.split()
                    self.chat_with_agent(agent_id)
                except ValueError:
                    print("Usage: /chat <agent_id>")
                except Exception as e:
                    print(f"⚠️ Chat error: {e}")
                    
            elif command.startswith("/knowledge"):
                try:
                    _, agent_id = command.split()
                    self.handle_knowledge_command(agent_id)
                except ValueError:
                    print("Usage: /knowledge <agent_id>")
                    
            elif command.startswith("/conversations"):
                try:
                    _, agent_id = command.split()
                    self.handle_conversations_command(agent_id)
                except ValueError:
                    print("Usage: /conversations <agent_id>")
                    
            elif command.startswith("/importAgents"):
                try:
                    _, connection_uri = command.split()
                    self.importAgentCores(connection_uri)
                except ValueError:
                    print("Usage: /importAgents <mongodb_uri>")
                except Exception as e:
                    print(f"⚠️ Import error: {e}")
                    
            elif command.startswith("/exportKnowledge"):
                try:
                    _, agent_id, file_path = command.split()
                    knowledge = list(self.db[f"knowledge_{agent_id}"].find())
                    with open(file_path, "w") as f:
                        json.dump(knowledge, f, indent=4)
                    print(f"Exported knowledge to: {file_path}")
                except ValueError:
                    print("Usage: /exportKnowledge <agent_id> <file_path>")
                    
            elif command.startswith("/importKnowledge"):
                try:
                    _, agent_id, file_path = command.split()
                    with open(file_path) as f:
                        knowledge = json.load(f)
                    collection = self.db[f"knowledge_{agent_id}"]
                    collection.insert_many(knowledge)
                    print(f"Imported {len(knowledge)} knowledge entries")
                except ValueError:
                    print("Usage: /importKnowledge <agent_id> <file_path>")
                    
            elif command == "/exit":
                break
                
            else:
                print("Invalid command. Type '/help' for options.")

    def handle_knowledge_command(self, agent_id: str):
        """Display and manage the agent's knowledge base."""
        try:
            # Get the knowledge collection for this agent
            collection_name = f"knowledge_{agent_id}"
            knowledge = self.db[collection_name].find().sort("last_updated", -1)
            
            if not knowledge.count():
                print("\nKnowledge base is empty. Use /add_knowledge to add entries.")
                return
                
            print("\nKnowledge Base Entries:")
            for entry in knowledge:
                print(f"\n[{entry['last_updated']}] {entry['topic']}")
                print("-" * len(entry['topic']))
                print(entry['content'])
                
        except Exception as e:
            print(f"⚠️ Error accessing knowledge base: {e}")
            
    def handle_conversations_command(self, agent_id: str):
        """List all saved conversations for an agent."""
        try:
            collection_name = f"conversations_{agent_id}"
            
            # Get unique conversation groups
            pipeline = [
                {"$match": {"save_name": {"$ne": None}}},
                {"$group": {
                    "_id": {
                        "save_name": "$save_name",
                        "session_id": "$session_id"
                    },
                    "start_date": {"$min": "$timestamp"}
                }},
                {"$sort": {"start_date": -1}}
            ]
            
            conversations = list(self.db[collection_name].aggregate(pipeline))
            
            if not conversations:
                print("\nNo saved conversations found.")
                return
                
            print("\nSaved Conversations:")
            for conv in conversations:
                session_id = conv["_id"]["session_id"]
                save_name = conv["_id"]["save_name"]
                start_date = conv["start_date"]
                
                # Get message count
                count = self.db[collection_name].count_documents({"session_id": session_id})
                
                print(f"\n[{start_date}] {save_name} ({count} messages)")
                
                # Get first exchange
                messages = list(self.db[collection_name]
                            .find({"session_id": session_id})
                            .sort("timestamp", 1)
                            .limit(2))
                            
                if messages:
                    print("Preview:")
                    print(f"User: {messages[0]['content'][:50]}...")
                    if len(messages) > 1:
                        print(f"Assistant: {messages[1]['content'][:50]}...")
                    
        except Exception as e:
            print(f"⚠️ Error accessing conversations: {e}")
        
    def handle_knowledge_import(self, agent_id: str, file_path: str):
        """Import knowledge base from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                import_data = json.load(f)
                
            collection_name = f"knowledge_{agent_id}"
            
            operations = []
            for entry in import_data["entries"]:
                operations.append(InsertOne({
                    "topic": entry["topic"],
                    "content": entry["content"],
                    "last_updated": entry["last_updated"],
                    "timestamp": time.time()
                }))
                
            if operations:
                result = self.db[collection_name].bulk_write(operations)
                print(f"\nImported {len(operations)} knowledge entries")
                
        except Exception as e:
            print(f"⚠️ Error importing knowledge base: {e}")

    def create_collection_with_schema(self, collection_name: str, indexes: list = None) -> None:
        """Create a new MongoDB collection with specified indexes.
            
        Args:
            collection_name: Name for the new collection
            indexes: List of index specifications to create
                
        Example:
            ```python
            # Create papers collection
            core.create_collection_with_schema(
                "papers",
                indexes=[
                    [("paper_id", 1)],  # Simple index
                    [("title", "text")], # Text index
                    [("published_date", -1)],  # Date index
                    [("metadata.field", 1)]  # Nested field index
                ]
            )
            ```
        """
        try:
            # Create collection
            collection = self.db[collection_name]
            
            # Create indexes if specified
            if indexes:
                for index_spec in indexes:
                    collection.create_index(index_spec)
                    
            print(f"Created collection: {collection_name}")
            return collection
            
        except Exception as e:
            print(f"Error creating collection: {str(e)}")
            raise

    def createDatabase(self, collection_name: str, indexes: list = None) -> None:
        """Create a new MongoDB collection for storing agent-related data.
        
        Creates a MongoDB collection with specified indexes for storing agent data.
        This is useful for adding custom storage capabilities to agents.

        Args:
            collection_name (str): Name for the new collection
            indexes (list): Optional list of index specifications

        Examples:
            Create a simple collection:
            >>> core = agentCores()
            >>> core.createDatabase("research_papers")

            Create with indexes:
            >>> core.createDatabase(
            ...     "citations", 
            ...     indexes=[
            ...         [("paper_id", 1)],
            ...         [("title", "text")]
            ...     ]
            ... )

        Notes:
            - Collections are created in the agentCores database
            - Indexes improve query performance for specific fields
            - Can be linked to agents using linkDatabase()
        """
        try:
            collection = self.create_collection_with_schema(
                collection_name,
                indexes=indexes
            )
            print(f"Created collection: {collection_name}")
            return collection
                
        except Exception as e:
            print(f"Error creating collection: {str(e)}")
            raise
    
    def execute_query(self, collection_name: str, query: Dict, projection: Dict = None) -> list:
        """Execute a MongoDB query and return results.
        
        Args:
            collection_name: Name of the MongoDB collection
            query: MongoDB query dictionary
            projection: Optional projection of fields to return
            
        Returns:
            list: Query results
            
        Example:
            ```python
            # Search papers collection
            results = core.execute_query(
                "research_papers",
                {"title": {"$regex": "neural networks", "$options": "i"}}
            )
            ```
        """
        return list(self.db[collection_name].find(query, projection))

    def execute_transaction(self, collection_name: str, operations: list) -> None:
        """Execute multiple MongoDB operations in a transaction.
        
        Args:
            collection_name: Name of the MongoDB collection
            operations: List of PyMongo operations (UpdateOne, InsertOne, etc.)
            
        Example:
            ```python
            # Insert multiple papers in a transaction
            operations = [
                InsertOne({"paper_id": "123", "title": "Paper 1"}),
                InsertOne({"paper_id": "456", "title": "Paper 2"})
            ]
            core.execute_transaction("research_papers", operations)
            ```
        """
        try:
            result = self.db[collection_name].bulk_write(operations)
            return result
        except Exception as e:
            print(f"Transaction failed: {e}")
            raise

    def bulk_insert(self, collection_name: str, documents: list) -> None:
        """Insert multiple documents into a MongoDB collection.
        
        Args:
            collection_name: Name of the MongoDB collection
            documents: List of documents to insert
            
        Example:
            ```python
            # Bulk insert papers
            documents = [
                {"paper_id": "123", "title": "Paper 1", "abstract": "Abstract 1"},
                {"paper_id": "456", "title": "Paper 2", "abstract": "Abstract 2"}
            ]
            core.bulk_insert("research_papers", documents)
            ```
        """
        try:
            result = self.db[collection_name].insert_many(documents)
            return result
        except Exception as e:
            print(f"Bulk insert failed: {e}")
            raise
            
    def chat_with_agent(self, agent_id: str):
        """Start an interactive chat session with a specified agent."""
        try:
            # Load agent
            agent = self.loadAgentCore(agent_id)
            if not agent:
                print(f"Agent '{agent_id}' not found.")
                return

            # Get collections
            collection_name = f"conversations_{agent_id}"
            conv_collection = self.db[collection_name]
            kb_collection = self.db[f"knowledge_{agent_id}"]
            
            # Create session
            session_id = f"{agent_id}_{int(time.time())}"

            while True:
                user_input = input("\nYou: ").strip()
                
                # Store message
                conv_collection.insert_one({
                    "timestamp": time.time(),
                    "role": "user",
                    "content": user_input,
                    "session_id": session_id
                })
                
                # Handle chat commands
                if user_input.startswith('/'):
                    if user_input == '/help':
                        print("\nChat Commands:")
                        print("  /history - Show recent conversation history")
                        print("  /knowledge - List entries in knowledge base")
                        print("  /clear - Clear conversation history")
                        print("  /save <title> - Save this conversation")
                        print("  /load <title> - Load a previous conversation")
                        print("  /add_knowledge <topic> <content> - Add to knowledge base")
                        print("  /help - Show these commands")
                        continue
                        
                    elif user_input == '/history':
                        history = conv_collection.find(
                            {"session_id": session_id}
                        ).sort("timestamp", -1).limit(10)
                        
                        for msg in history:
                            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['timestamp']))}] {msg['role']}: {msg['content']}")
                        continue
                        
                    elif user_input == '/knowledge':
                        knowledge = kb_collection.find().sort("last_updated", -1)
                        for entry in knowledge:
                            print(f"\n[{entry['last_updated']}] {entry['topic']}:")
                            content = entry['content']
                            print(content[:100] + "..." if len(content) > 100 else content)
                        continue
                        
                    elif user_input == '/clear':
                        conv_collection.delete_many({"session_id": session_id})
                        print("\nConversation history cleared.")
                        continue
                        
                    elif user_input.startswith('/save '):
                        title = user_input[6:].strip()
                        conv_collection.update_many(
                            {"session_id": session_id},
                            {"$set": {"save_name": title}}
                        )
                        print(f"\nConversation saved as '{title}'")
                        continue
                        
                    elif user_input.startswith('/load '):
                        title = user_input[6:].strip()
                        loaded = conv_collection.find(
                            {"save_name": title}
                        ).sort("timestamp", 1)
                        
                        messages = list(loaded)
                        if messages:
                            print(f"\nLoaded conversation '{title}':")
                            for msg in messages:
                                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['timestamp']))}] {msg['role']}: {msg['content']}")
                        else:
                            print(f"\nNo saved conversation found with title '{title}'")
                        continue
                        
                    elif user_input.startswith('/add_knowledge '):
                        try:
                            _, topic, *content_parts = user_input.split(maxsplit=2)
                            content = content_parts[0] if content_parts else ""
                            kb_collection.insert_one({
                                "topic": topic,
                                "content": content,
                                "last_updated": time.time(),
                                "timestamp": time.time()
                            })
                            print(f"\nAdded knowledge entry under topic '{topic}'")
                        except ValueError:
                            print("Usage: /add_knowledge <topic> <content>")
                        continue

                if user_input.lower() == 'exit':
                    print("\nEnding chat session...")
                    break

                # Get model from agent config
                model_config = agent["agentCore"]["models"]["largeLanguageModel"]
                if not model_config.get("names"):
                    print("No language model configured for this agent")
                    continue
                    
                model = model_config["names"][0]

                # Build system prompt
                system_prompt = (
                    f"{agent['agentCore']['prompts']['userInput']} "
                    f"{agent['agentCore']['prompts']['agent']['llmSystem']} "
                    f"{agent['agentCore']['prompts']['agent']['llmBooster']}"
                )

                # Get relevant knowledge
                relevant_knowledge = kb_collection.find(
                    {"$text": {"$search": user_input}},
                    {"score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})]).limit(3)

                # Add knowledge context to prompt
                context_prompt = system_prompt
                knowledge_texts = list(relevant_knowledge)
                if knowledge_texts:
                    context = "\n".join(k['content'] for k in knowledge_texts)
                    context_prompt += f"\nRelevant context: {context}"

                try:
                    import ollama
                    
                    # Stream the response
                    print("\nAssistant: ", end='', flush=True)
                    response_text = ""
                    
                    stream = ollama.chat(
                        model=model,
                        messages=[
                            {'role': 'system', 'content': context_prompt},
                            {'role': 'user', 'content': user_input}
                        ],
                        stream=True
                    )

                    for chunk in stream:
                        chunk_text = chunk['message']['content']
                        print(chunk_text, end='', flush=True)
                        response_text += chunk_text

                    # Store assistant response
                    conv_collection.insert_one({
                        "timestamp": time.time(),
                        "role": "assistant",
                        "content": response_text,
                        "session_id": session_id
                    })
                    
                    print()  # New line after response

                except ImportError:
                    print("Ollama not available. Install with: pip install ollama")
                    break
                except Exception as e:
                    print(f"\nError in chat: {str(e)}")
                    continue

        except Exception as e:
            print(f"\n⚠️ Error in chat session: {e}")

    def basic_ollama_chat(self, agent_id: str, message: str, stream: bool = True) -> Optional[str]:
        """Simple Ollama chat using agent's database configuration."""
        try:
            import ollama
        except ImportError:
            return "Ollama not available. Install with: pip install ollama"
            
        # Load agent configuration
        agent = self.loadAgentCore(agent_id)
        if not agent:
            return f"Agent '{agent_id}' not found"
            
        # Get model from agent config
        model_config = agent["agentCore"]["models"]["largeLanguageModel"]
        if not model_config.get("names"):
            return "No language model configured for this agent"
        
        model = model_config["names"][0]
        
        try:
            # Get collections
            conv_collection = self.db[f"conversations_{agent_id}"]
            
            # Create session ID
            session_id = f"{agent_id}_{int(time.time())}"
            
            # Build system prompt
            system_prompt = (
                f"{agent['agentCore']['prompts']['userInput']} "
                f"{agent['agentCore']['prompts']['agent']['llmSystem']} "
                f"{agent['agentCore']['prompts']['agent']['llmBooster']}"
            )
            
            # Store user message
            conv_collection.insert_one({
                "timestamp": time.time(),
                "role": "user",
                "content": message,
                "session_id": session_id
            })
            
            # Chat with model and handle response
            response_text = ""
            
            if stream:
                # Stream response
                print("\nAssistant: ", end="", flush=True)
                stream = ollama.chat(
                    model=model,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': message}
                    ],
                    stream=True
                )
                
                for chunk in stream:
                    chunk_text = chunk['message']['content']
                    print(chunk_text, end='', flush=True)
                    response_text += chunk_text
                print()  # New line after response
                
            else:
                # Single response
                response = ollama.chat(
                    model=model,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': message}
                    ]
                )
                response_text = response['message']['content']
            
            # Store assistant response
            conv_collection.insert_one({
                "timestamp": time.time(),
                "role": "assistant",
                "content": response_text,
                "session_id": session_id
            })
                
            return response_text
            
        except Exception as e:
            return f"Error in chat: {str(e)}"