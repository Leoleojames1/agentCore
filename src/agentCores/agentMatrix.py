# agentMatrix.py
"""agentMatrix

A SQLite-based storage system for managing AI agent configurations and states.

This module provides a simple but robust storage implementation for agent cores,
maintaining exact structure and versioning in SQLite. It handles the persistence
layer for the agentCores package, providing CRUD operations for agent configurations.

Features:
- Efficient SQLite-based storage
- Version tracking for agent configurations
- Unique identifier management
- Metadata support for agent cores
- Bulk operations support

Example:
    ```python
    from agentCores import agentMatrix
    
    # Initialize storage
    matrix = agentMatrix("agents.db")
    
    # Store agent configuration
    matrix.upsert(
        documents=[agent_config],
        ids=["agent1"],
        metadatas=[{"save_date": "2024-12-11"}]
    )
    
    # Retrieve configurations
    agents = matrix.get(ids=["agent1"])
    ```

Author: Leo Borcherding
Version: 0.2.1
Date: 2024-12-11
License: MIT
"""

from pymongo import MongoClient
import json
from typing import Optional, Dict
import time

class agentMatrix:
    """MongoDB implementation of agent matrix storage."""
    def __init__(self, connection_uri: str = "mongodb://localhost:27017/"):
        """Initialize MongoDB connection and collections."""
        self.client = MongoClient(connection_uri)
        self.db = self.client.agentCores
        
        # Initialize collections
        self.agent_cores = self.db.agent_cores
        self.templates = self.db.templates
        self.design_patterns = self.db.design_patterns
        
        # Create indexes
        self.agent_cores.create_index("agent_id", unique=True)
        self.templates.create_index("template_id", unique=True)
        self.design_patterns.create_index("pattern_id", unique=True)

    def upsert(self, documents: list, ids: list, metadatas: list = None) -> None:
        """Store agent core(s) in MongoDB."""
        for idx, (doc, id_) in enumerate(zip(documents, ids)):
            metadata = metadatas[idx] if metadatas else {'save_date': None}
            
            # Always serialize to JSON string for storage
            core_data = json.dumps(doc)
            
            self.agent_cores.update_one(
                {"agent_id": id_},
                {
                    "$set": {
                        "core_data": core_data,
                        "save_date": metadata.get('save_date'),
                        "last_updated": time.time()
                    }
                },
                upsert=True
            )

    def get(self, ids: Optional[list] = None) -> Dict:
        """Retrieve agent core(s) from MongoDB."""
        query = {"agent_id": {"$in": ids}} if ids else {}
        results = list(self.agent_cores.find(query))
        
        return {
            "ids": [r["agent_id"] for r in results],
            # Always parse stored JSON strings
            "documents": [json.loads(r["core_data"]) for r in results],
            "metadatas": [{"agent_id": r["agent_id"], "save_date": r["save_date"]} 
                        for r in results]
        }

    def delete(self, ids: list) -> None:
        """Remove agent core(s) from MongoDB."""
        self.agent_cores.delete_many({"agent_id": {"$in": ids}})
            
    def store_template(self, template_name: str, template_data: Dict, metadata: Dict = None) -> str:
        """Store a template in MongoDB."""
        import hashlib
        template_id = hashlib.sha256(
            json.dumps(template_data, sort_keys=True).encode()
        ).hexdigest()[:8]
        
        self.templates.update_one(
            {"template_id": template_id},
            {
                "$set": {
                    "template_name": template_name,
                    "template_data": template_data,
                    "origin_source": "user_defined",
                    "origin_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "metadata": metadata or {}
                }
            },
            upsert=True
        )
        return template_id

    def get_template(self, template_name: str) -> Optional[Dict]:
        """Retrieve a template by name."""
        result = self.templates.find_one({"template_name": template_name})
        return result["template_data"] if result else None