"""
Model adapter system for OpenChronicle.
Provides a unified interface for different LLM backends (OpenAI, Ollama, local models).
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

class ModelAdapter(ABC):
    """Abstract base class for model adapters."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get("model_name", "unknown")
        self.max_tokens = config.get("max_tokens", 2048)
        self.temperature = config.get("temperature", 0.7)
        self.initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the model adapter."""
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the model."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        pass
    
    def log_interaction(self, story_id: str, prompt: str, response: str, metadata: Dict[str, Any] = None):
        """Log the interaction for debugging/analysis."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "story_id": story_id,
            "model": self.model_name,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "metadata": metadata or {}
        }
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join("storage", story_id, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Log to file
        log_file = os.path.join(logs_dir, "model_interactions.jsonl")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

class OpenAIAdapter(ModelAdapter):
    """OpenAI GPT adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize OpenAI client."""
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("openai package required for OpenAI adapter")
        except Exception as e:
            print(f"Failed to initialize OpenAI adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a creative storytelling assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                stop=kwargs.get("stop_sequences", None)
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information."""
        return {
            "provider": "OpenAI",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class OllamaAdapter(ModelAdapter):
    """Ollama local model adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Ollama client."""
        try:
            import httpx
            self.client = httpx.AsyncClient(base_url=self.base_url)
            
            # Test connection
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                self.initialized = True
                return True
            else:
                print(f"Ollama connection failed: {response.status_code}")
                return False
        except ImportError:
            raise ImportError("httpx package required for Ollama adapter")
        except Exception as e:
            print(f"Failed to initialize Ollama adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Ollama."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens)
                }
            }
            
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information."""
        return {
            "provider": "Ollama",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class MockAdapter(ModelAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.responses = config.get("responses", [
            "This is a mock response.",
            "Another mock response for testing.",
            "A third mock response to cycle through."
        ])
        self.response_index = 0
    
    async def initialize(self) -> bool:
        """Initialize mock adapter."""
        self.initialized = True
        return True
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate mock response."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        # Check if this is an analysis prompt
        if "JSON format" in prompt and "content_type" in prompt:
            # Generate mock analysis JSON
            content_types = ["action", "dialogue", "description", "question", "command"]
            entities = {
                "characters": [],
                "locations": [],
                "items": [],
                "emotions": ["curious", "determined", "excited"]
            }
            
            # Extract some basic info from the prompt
            if "sword" in prompt.lower():
                entities["items"].append("sword")
            if "dragon" in prompt.lower():
                entities["characters"].append("dragon")
            if "castle" in prompt.lower():
                entities["locations"].append("castle")
            if "forest" in prompt.lower():
                entities["locations"].append("forest")
            
            # Determine content type
            if "?" in prompt:
                content_type = "question"
            elif "say" in prompt.lower() or "hello" in prompt.lower():
                content_type = "dialogue"
            elif "look" in prompt.lower() or "see" in prompt.lower():
                content_type = "description"
            else:
                content_type = "action"
            
            # Generate mock analysis
            analysis = {
                "content_type": content_type,
                "intent": "User wants to interact with the story",
                "entities": entities,
                "content_flags": {
                    "nsfw": False,
                    "violence": "battle" in prompt.lower() or "fight" in prompt.lower(),
                    "mature_themes": False,
                    "emotional_intensity": "medium"
                },
                "required_canon": [],
                "memory_triggers": [],
                "response_style": "narrative",
                "token_priority": "medium"
            }
            
            return json.dumps(analysis, indent=2)
        
        # Regular story response
        # Cycle through responses
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        
        # Add some variation based on prompt length
        if len(prompt) > 500:
            response += " [Extended response for longer prompt]"
        
        return response
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get mock model information."""
        return {
            "provider": "Mock",
            "model_name": self.model_name,
            "responses_count": len(self.responses),
            "current_index": self.response_index,
            "initialized": self.initialized
        }

class ModelManager:
    """Manages model adapters and provides unified access."""
    
    def __init__(self):
        self.adapters: Dict[str, ModelAdapter] = {}
        self.default_adapter = None
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration."""
        config_file = os.path.join("config", "models.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # Default configuration
        return {
            "default_adapter": "mock",
            "adapters": {
                "openai": {
                    "type": "openai",
                    "model_name": "gpt-4o-mini",
                    "max_tokens": 2048,
                    "temperature": 0.7
                },
                "ollama": {
                    "type": "ollama",
                    "model_name": "llama3.2",
                    "base_url": "http://localhost:11434",
                    "max_tokens": 2048,
                    "temperature": 0.7
                },
                "mock": {
                    "type": "mock",
                    "model_name": "mock-model",
                    "responses": [
                        "The story continues with rich detail and engaging narrative.",
                        "Your character moves forward, discovering new possibilities.",
                        "The world around you shifts as the tale unfolds."
                    ]
                }
            }
        }
    
    def register_adapter(self, name: str, adapter: ModelAdapter):
        """Register a model adapter."""
        self.adapters[name] = adapter
    
    async def initialize_adapter(self, name: str) -> bool:
        """Initialize a specific adapter."""
        if name not in self.config["adapters"]:
            raise ValueError(f"Adapter '{name}' not found in configuration")
        
        adapter_config = self.config["adapters"][name]
        adapter_type = adapter_config["type"]
        
        if adapter_type == "openai":
            adapter = OpenAIAdapter(adapter_config)
        elif adapter_type == "ollama":
            adapter = OllamaAdapter(adapter_config)
        elif adapter_type == "mock":
            adapter = MockAdapter(adapter_config)
        else:
            raise ValueError(f"Unknown adapter type: {adapter_type}")
        
        success = await adapter.initialize()
        if success:
            self.adapters[name] = adapter
            if self.default_adapter is None:
                self.default_adapter = name
        
        return success
    
    async def generate_response(self, prompt: str, adapter_name: str = None, story_id: str = None, **kwargs) -> str:
        """Generate response using specified or default adapter."""
        adapter_name = adapter_name or self.default_adapter
        
        if adapter_name not in self.adapters:
            # Try to initialize the adapter
            if not await self.initialize_adapter(adapter_name):
                raise RuntimeError(f"Failed to initialize adapter: {adapter_name}")
        
        adapter = self.adapters[adapter_name]
        response = await adapter.generate_response(prompt, **kwargs)
        
        # Log interaction if story_id provided
        if story_id:
            metadata = {"adapter": adapter_name, "kwargs": kwargs}
            adapter.log_interaction(story_id, prompt, response, metadata)
        
        return response
    
    def get_available_adapters(self) -> List[str]:
        """Get list of available adapters."""
        return list(self.config["adapters"].keys())
    
    def get_adapter_info(self, name: str) -> Dict[str, Any]:
        """Get information about a specific adapter."""
        if name in self.adapters:
            return self.adapters[name].get_model_info()
        elif name in self.config["adapters"]:
            config = self.config["adapters"][name]
            return {
                "provider": config["type"],
                "model_name": config.get("model_name", "unknown"),
                "initialized": False
            }
        else:
            raise ValueError(f"Adapter '{name}' not found")
    
    async def shutdown(self):
        """Shutdown all adapters."""
        for adapter in self.adapters.values():
            if hasattr(adapter, 'client') and adapter.client:
                if hasattr(adapter.client, 'aclose'):
                    await adapter.client.aclose()

# Global model manager instance
model_manager = ModelManager()
