from agentCores import agentCores
from duckduckgo_search import DDGS
import time
from pymongo.errors import OperationFailure
import json

class researchAssistant:
    def __init__(self, agent_id: str = "phi3_research_assistant", connection_uri: str = "mongodb://localhost:27017/"):
        """Initialize research assistant with MongoDB storage."""
        try:
            self.core = agentCores(connection_uri=connection_uri)
            self.agent_id = agent_id
            
            # Create agent with research configuration
            agent_config = {
                "agentCore": {
                    "identifyers": {
                        "agent_id": agent_id,
                        "uid": None,
                        "version": 1,
                        "creationDate": time.time()
                    },
                    "models": {
                        "largeLanguageModel": {
                            "names": ["phi3"],
                            "instances": None,
                            "model_config_template": {}
                        }
                    },
                    "prompts": {
                        "userInput": "Help users research topics and understand information",
                        "agent": {
                            "llmSystem": "You are a research assistant. Combine search results with your knowledge to give clear answers.",
                            "llmBooster": "For each response: Summarize search results, add relevant context, and cite sources.",
                            "visionSystem": None,
                            "visionBooster": None
                        }
                    },
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
                        "ACTIVE_AGENT_FLAG": True
                    }
                }
            }
            
            # Load or create agent
            existing_agent = self.core.loadAgentCore(agent_id)
            if not existing_agent:
                self.agent = self.core.mintAgent(
                    agent_id=agent_id,
                    model_config=agent_config["agentCore"]["models"],
                    prompt_config=agent_config["agentCore"]["prompts"],
                    command_flags=agent_config["agentCore"]["modalityFlags"]
                )
            else:
                self.agent = existing_agent
            
            # Get database collections based on agent ID
            self.research_collection = f"research_{agent_id}"
            self.knowledge_collection = f"knowledge_{agent_id}"
            self.conversation_collection = f"conversations_{agent_id}"
            
            # Create indexes safely
            self._ensure_indexes()
            
        except Exception as e:
            raise Exception(f"Failed to initialize researchAssistant: {str(e)}")
    
    def _ensure_indexes(self):
        """Safely create necessary indexes for collections."""
        try:
            # Research collection indexes
            self.core.db[self.research_collection].create_index([("timestamp", -1)])
            self.core.db[self.research_collection].create_index([("title", 1)])
            try:
                self.core.db[self.research_collection].create_index([("query", "text"), ("content", "text")])
            except OperationFailure:
                # Text index already exists, skip
                pass
            
            # Knowledge collection indexes
            self.core.db[self.knowledge_collection].create_index([("last_updated", -1)])
            try:
                self.core.db[self.knowledge_collection].create_index([("content", "text")])
            except OperationFailure:
                pass
            
            # Conversation collection indexes
            self.core.db[self.conversation_collection].create_index([("session_id", 1)])
            self.core.db[self.conversation_collection].create_index([("timestamp", -1)])
            
        except Exception as e:
            print(f"Warning: Error creating some indexes: {str(e)}")
    
    def search(self, query: str) -> list:
        """Perform search and store in MongoDB research collection."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                
                # Store results in MongoDB
                documents = []
                current_time = time.time()
                
                for result in results:
                    documents.append({
                        "query": query,
                        "title": result.get('title', ''),
                        "content": result.get('body', ''),
                        "url": result.get('link', ''),
                        "timestamp": current_time
                    })
                
                if documents:
                    self.core.db[self.research_collection].insert_many(documents)
                    
                return results
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def get_recent_research(self, query: str, limit: int = 3) -> list:
        """Get recent research results for a query."""
        try:
            return list(self.core.db[self.research_collection].find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([
                ("score", {"$meta": "textScore"}),
                ("timestamp", -1)
            ]).limit(limit))
        except Exception as e:
            print(f"Error retrieving research: {str(e)}")
            return []

    def process_query(self, query: str) -> str:
        """Process a research query using search results and Ollama."""
        try:
            import ollama
            
            # Get search results
            results = self.search(query)
            prev_results = self.get_recent_research(query)
            
            # Format search context
            context = "Based on these search results:\n\n"
            for i, r in enumerate(results, 1):
                context += f"{i}. {r.get('title', '')}\n{r.get('body', '')}\n\n"
                
            if prev_results:
                context += "\nRelevant previous research:\n\n"
                for i, r in enumerate(prev_results, 1):
                    context += f"{i}. {r['title']}\n{r['content']}\n\n"
            
            # Get model and prompts from stored agent configuration
            model = self.agent["agentCore"]["models"]["largeLanguageModel"]["names"][0]
            prompts = self.agent["agentCore"]["prompts"]
            system_prompt = prompts['agent']['llmSystem']
            
            print("Debug: Agent configuration:")
            print(json.dumps(self.agent, indent=2))

            print("Debug: Model:", model)
            print("Debug: Prompts:", json.dumps(prompts, indent=2))

            try:
                response = ollama.chat(
                    model=model,
                    messages=[
                        {
                            'role': 'system', 
                            'content': system_prompt,
                        },
                        {'role': 'user', 
                         'content': f"{prompts['agent']['llmBooster']} {prompts['userInput']} {context}\nUser question: {query}"
                        }
                    ]
                )
            except Exception as ollama_error:
                print(f"Debug: Ollama chat error: {str(ollama_error)}")
                return f"Error in Ollama chat: {str(ollama_error)}"
            
            # Store conversation
            session_id = f"{self.agent_id}_{int(time.time())}"
            self.core.db[self.conversation_collection].insert_many([
                {
                    "timestamp": time.time(),
                    "role": "user",
                    "content": query,
                    "session_id": session_id
                },
                {
                    "timestamp": time.time(),
                    "role": "assistant",
                    "content": response['message']['content'],
                    "session_id": session_id
                }
            ])
            
            return response['message']['content']
            
        except ImportError:
            return "Error: Ollama not installed. Install with: pip install ollama"
        except Exception as e:
            print(f"Debug: Error in process_query: {str(e)}")
            return f"Error processing query: {str(e)}"

    def start_chat(self):
        """Start interactive chat session with research capabilities."""
        print("\nResearch Assistant Ready!")
        print("Type 'exit' to end or '/help' for commands")
        
        while True:
            try:
                query = input("\nYou: ").strip()
                
                if query.lower() == 'exit':
                    break
                    
                if query.startswith('/'):
                    if query == '/help':
                        print("\nCommands:")
                        print("  /history - Show recent searches")
                        print("  /clear - Clear research history")
                        print("  /save <title> - Save this research session")
                        print("  /help - Show these commands")
                        continue
                        
                    elif query == '/history':
                        recent = self.core.db[self.research_collection].find().sort(
                            "timestamp", -1
                        ).limit(5)
                        
                        print("\nRecent Research:")
                        for entry in recent:
                            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry['timestamp']))}]")
                            print(f"Query: {entry['query']}")
                            print(f"Title: {entry['title']}")
                            print(f"URL: {entry['url']}")
                        continue
                        
                    elif query == '/clear':
                        self.core.db[self.research_collection].delete_many({})
                        print("\nResearch history cleared.")
                        continue
                        
                    elif query.startswith('/save '):
                        title = query[6:].strip()
                        self.core.db[self.research_collection].update_many(
                            {"timestamp": {"$gt": time.time() - 3600}},  # Last hour
                            {"$set": {"session_title": title}}
                        )
                        print(f"\nResearch session saved as '{title}'")
                        continue
                
                response = self.process_query(query)
                print("\nAssistant:", response)
                
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again or type 'exit' to quit")

def main():
    try:
        assistant = researchAssistant()
        assistant.start_chat()
    except Exception as e:
        print(f"Error initializing assistant: {str(e)}")
        return

if __name__ == "__main__":
    main()
