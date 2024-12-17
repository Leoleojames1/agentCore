from pymongo import MongoClient
import threading
from contextlib import contextmanager
from typing import Dict, Optional, Any
import time
import logging

class databaseManager:
    def __init__(self, connection_uri: str = "mongodb://localhost:27017/"):
        """Initialize MongoDB connection."""
        self.client = MongoClient(connection_uri)
        self.db = self.client.agentCores
        self.collections = {}

    def create_collection(self, collection_name: str, indexes: list = None):
        """Create a MongoDB collection with optional indexes."""
        collection = self.db[collection_name]
        if indexes:
            for index in indexes:
                collection.create_index(index)
        self.collections[collection_name] = collection
        return collection

    def optimize_database(self, collection_name: str):
        """Optimize MongoDB collection."""
        # MongoDB handles most optimization automatically
        pass

    def _cleanup_database(self, collection_name: str):
        """Perform MongoDB collection maintenance."""
        try:
            # Remove old conversations
            self.db[collection_name].delete_many({
                "timestamp": {"$lt": time.time() - (30 * 24 * 60 * 60)},  # 30 days
                "save_name": None
            })
            
            # Clean up old embeddings
            if "embeddings" in collection_name:
                self.db[collection_name].delete_many({
                    "last_used": {"$lt": time.time() - (90 * 24 * 60 * 60)}  # 90 days
                })
                
        except Exception as e:
            logging.error(f"Error during collection cleanup: {e}")

    def _cleanup_loop(self):
        """Background thread for periodic cleanup."""
        while True:
            current_time = time.time()
            for db_path, last_cleanup in self.last_cleanup.items():
                if current_time - last_cleanup > self.cleanup_interval:
                    self._cleanup_database(db_path)
            time.sleep(60)  # Check every minute

    def close_all(self):
        """Close MongoDB connection."""
        self.client.close()