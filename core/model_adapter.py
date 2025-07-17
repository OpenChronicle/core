"""
Model adapter system for OpenChronicle.
Provides a unified interface for different LLM backends (OpenAI, Ollama, local models).
"""

import json
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_model_interaction, log_system_event, log_info, log_error

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
        # Use centralized logging system
        log_model_interaction(
            story_id=story_id,
            model=self.model_name,
            prompt_length=len(prompt),
            response_length=len(response),
            metadata=metadata or {}
        )
        
        # Maintain backward compatibility with local file logging
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
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize OpenAI client."""
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("openai package required for OpenAI adapter")
        except Exception as e:
            log_error(f"Failed to initialize OpenAI adapter: {e}")
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
                log_info(f"Ollama adapter initialized successfully for {self.model_name}")
                return True
            else:
                log_error(f"Ollama connection failed: {response.status_code}")
                return False
        except ImportError:
            raise ImportError("httpx package required for Ollama adapter")
        except Exception as e:
            log_error(f"Failed to initialize Ollama adapter: {e}")
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
        """Load model configuration with plugin-style support."""
        # First, try to load the new model registry
        registry_file = os.path.join("config", "model_registry.json")
        if os.path.exists(registry_file):
            log_system_event("model_config_loading", "Loading plugin-style model configuration from registry")
            return self._load_plugin_config(registry_file)
        
        # Fallback to legacy models.json
        config_file = os.path.join("config", "models.json")
        if os.path.exists(config_file):
            log_system_event("model_config_loading", "Loading legacy models.json configuration")
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # Default configuration
        log_system_event("model_config_loading", "Using default model configuration")
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

    def _load_plugin_config(self, registry_file: str) -> Dict[str, Any]:
        """Load plugin-style model configuration from registry and individual files."""
        log_info("Loading plugin-style model configuration")
        log_system_event("plugin_config_loading", f"Loading plugin-style model configuration from {registry_file}")
        
        # Load the registry
        with open(registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        
        log_system_event("plugin_config_registry", f"Loaded registry with {len(registry['models'])} model entries")
        
        # Load individual model configurations
        models_dir = os.path.join("config", "models")
        adapters = {}
        
        for model_entry in registry["models"]:
            provider = model_entry["name"]  # Use "name" field from registry
            model_file = os.path.join(models_dir, f"{provider}.json")
            
            if os.path.exists(model_file) and model_entry["enabled"]:
                try:
                    with open(model_file, "r", encoding="utf-8") as f:
                        model_config = json.load(f)
                    
                    if model_config.get("enabled", True):
                        # Convert plugin config to legacy format for compatibility
                        adapter_config = {
                            "type": model_config["type"],
                            "model_name": model_config["api_config"]["model_name"],
                            "base_url": model_config["api_config"]["base_url"],
                            "api_key": model_config["api_config"].get("api_key", ""),
                            "api_key_env": model_config["api_config"].get("api_key_env", ""),
                            "max_tokens": model_config["limits"]["max_tokens"],
                            "temperature": model_config["generation_params"]["temperature"],
                            "top_p": model_config["generation_params"].get("top_p", 0.9),
                            "top_k": model_config["generation_params"].get("top_k", 40),
                            "retry_config": model_config["retry_config"],
                            "content_filtering": model_config["content_filtering"],
                            "capabilities": model_config["capabilities"],
                            "limits": model_config["limits"],
                            "available_models": model_config["available_models"],
                            "health_check": model_config["health_check"]
                        }
                        
                        # Add provider-specific configurations
                        if provider == "openai":
                            adapter_config["organization"] = model_config["api_config"].get("organization", "")
                        elif provider == "anthropic":
                            adapter_config["version"] = model_config["api_config"].get("version", "2023-06-01")
                        elif provider == "google":
                            adapter_config["version"] = model_config["api_config"].get("version", "v1beta")
                        elif provider == "mock":
                            adapter_config["responses"] = [
                                "The story continues with rich detail and engaging narrative.",
                                "Your character moves forward, discovering new possibilities.",
                                "The world around you shifts as the tale unfolds."
                            ]
                        
                        adapters[provider] = adapter_config
                        log_info(f"Loaded model configuration for {provider}")
                        log_system_event("model_config_loaded", f"Loaded model configuration for {provider}")
                        
                except Exception as e:
                    log_error(f"Failed to load model config for {provider}: {e}")
                    log_system_event("model_config_error", f"Failed to load model config for {provider}: {e}")
        
        # Add mock adapter if no other adapters loaded
        if not adapters:
            adapters["mock"] = {
                "type": "mock",
                "model_name": "mock-model",
                "responses": [
                    "The story continues with rich detail and engaging narrative.",
                    "Your character moves forward, discovering new possibilities.",
                    "The world around you shifts as the tale unfolds."
                ]
            }
            log_system_event("model_config_fallback", "No adapters loaded, using mock adapter as fallback")
        
        # Build fallback chains from registry
        fallback_chains = {}
        for model_entry in registry["models"]:
            provider = model_entry["name"]
            fallbacks = model_entry.get("fallbacks", [])
            # Ensure the provider itself is included in the chain
            if provider not in fallbacks:
                fallbacks.insert(0, provider)
            fallback_chains[provider] = fallbacks
        
        # Build final configuration
        default_adapter = registry["default_model"]
        
        # If the default adapter didn't load, find the first available one
        if default_adapter not in adapters:
            if adapters:
                default_adapter = list(adapters.keys())[0]
                log_info(f"Default adapter '{registry['default_model']}' not available, using '{default_adapter}'")
            else:
                default_adapter = "mock"
                log_info("No adapters loaded, defaulting to mock")
        
        config = {
            "default_adapter": default_adapter,
            "adapters": adapters,
            "fallback_chains": fallback_chains,
            "content_routing": registry["content_routing"],
            "registry_version": registry["version"]
        }
        
        log_info(f"Plugin-style configuration loaded with {len(adapters)} adapters")
        return config
    
    def register_adapter(self, name: str, adapter: ModelAdapter):
        """Register a model adapter."""
        self.adapters[name] = adapter
    
    async def initialize_adapter(self, name: str) -> bool:
        """Initialize a specific adapter."""
        if name not in self.config["adapters"]:
            log_system_event("adapter_initialization", f"Adapter {name} not found in configuration")
            raise ValueError(f"Adapter '{name}' not found in configuration")
        
        adapter_config = self.config["adapters"][name]
        adapter_type = adapter_config["type"]
        
        log_system_event("adapter_initialization", f"Initializing {adapter_type} adapter: {name}")
        
        try:
            if adapter_type == "openai":
                adapter = OpenAIAdapter(adapter_config)
            elif adapter_type == "ollama":
                adapter = OllamaAdapter(adapter_config)
            elif adapter_type == "mock":
                adapter = MockAdapter(adapter_config)
            elif adapter_type == "anthropic":
                adapter = AnthropicAdapter(adapter_config)
            elif adapter_type == "gemini":
                adapter = GeminiAdapter(adapter_config)
            elif adapter_type == "groq":
                adapter = GroqAdapter(adapter_config)
            elif adapter_type == "cohere":
                adapter = CohereAdapter(adapter_config)
            elif adapter_type == "mistral":
                adapter = MistralAdapter(adapter_config)
            elif adapter_type == "huggingface":
                adapter = HuggingFaceAdapter(adapter_config)
            elif adapter_type == "azure_openai":
                adapter = AzureOpenAIAdapter(adapter_config)
            elif adapter_type == "openai_image":
                adapter = OpenAIImageAdapter(adapter_config)
            elif adapter_type == "stability":
                adapter = StabilityAdapter(adapter_config)
            elif adapter_type == "replicate":
                adapter = ReplicateAdapter(adapter_config)
            elif adapter_type == "mock_image":
                adapter = MockImageAdapter(adapter_config)
            else:
                log_system_event("adapter_initialization", f"Unknown adapter type: {adapter_type}")
                raise ValueError(f"Unknown adapter type: {adapter_type}")
            
            success = await adapter.initialize()
            if success:
                self.adapters[name] = adapter
                if self.default_adapter is None:
                    self.default_adapter = name
                log_system_event("adapter_initialization", f"Successfully initialized {adapter_type} adapter: {name}")
            else:
                log_system_event("adapter_initialization", f"Failed to initialize {adapter_type} adapter: {name}")
        
        except Exception as e:
            log_system_event("adapter_initialization", f"Error initializing {adapter_type} adapter {name}: {e}")
            raise
        
        return success
    
    async def generate_response(self, prompt: str, adapter_name: str = None, story_id: str = None, **kwargs) -> str:
        """Generate response using specified or default adapter with fallback support."""
        adapter_name = adapter_name or self.default_adapter
        
        # Use fallback chain if configured
        if "fallback_chains" in self.config and adapter_name in self.config["fallback_chains"]:
            chain = self.config["fallback_chains"][adapter_name]
            log_info(f"Using fallback chain for {adapter_name}: {chain}")
            log_system_event("fallback_chain_usage", f"Using fallback chain for {adapter_name}: {chain}")
            
            for attempt_adapter in chain:
                try:
                    if attempt_adapter not in self.adapters:
                        # Try to initialize the adapter
                        if not await self.initialize_adapter(attempt_adapter):
                            log_error(f"Failed to initialize adapter: {attempt_adapter}")
                            continue
                    
                    adapter = self.adapters[attempt_adapter]
                    response = await adapter.generate_response(prompt, **kwargs)
                    
                    # Log interaction if story_id provided
                    if story_id:
                        metadata = {"adapter": attempt_adapter, "kwargs": kwargs, "fallback_position": chain.index(attempt_adapter)}
                        adapter.log_interaction(story_id, prompt, response, metadata)
                    
                    log_info(f"Successfully generated response using {attempt_adapter}")
                    log_system_event("fallback_chain_success", f"Successfully generated response using {attempt_adapter} (fallback position {chain.index(attempt_adapter)})")
                    return response
                    
                except Exception as e:
                    log_error(f"Adapter {attempt_adapter} failed: {e}")
                    log_system_event("fallback_chain_failure", f"Adapter {attempt_adapter} failed: {e}")
                    continue
            
            # If all adapters in chain failed, raise error
            log_system_event("fallback_chain_exhausted", f"All adapters in fallback chain failed for {adapter_name}")
            raise RuntimeError(f"All adapters in fallback chain failed for {adapter_name}")
        
        # Original single adapter logic
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
    
    async def check_adapter_health(self, adapter_name: str) -> Dict[str, Any]:
        """Check the health of a specific adapter."""
        if adapter_name not in self.config["adapters"]:
            return {"status": "unknown", "error": "Adapter not found in configuration"}
        
        adapter_config = self.config["adapters"][adapter_name]
        health_check = adapter_config.get("health_check", {})
        
        if not health_check:
            return {"status": "unknown", "error": "No health check configured"}
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=health_check.get("timeout", 10)) as client:
                if health_check["method"] == "GET":
                    response = await client.get(health_check["endpoint"])
                else:
                    response = await client.post(health_check["endpoint"], json={"test": "health_check"})
                
                if response.status_code == health_check["expected_status"]:
                    return {"status": "healthy", "response_time": response.elapsed.total_seconds()}
                else:
                    return {"status": "unhealthy", "error": f"Unexpected status: {response.status_code}"}
        
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def get_adapter_for_content(self, content_type: str, content_flags: Dict[str, Any] = None) -> str:
        """Get the best adapter for specific content type based on content routing rules."""
        if "content_routing" not in self.config:
            return self.default_adapter
        
        routing_rules = self.config["content_routing"]
        content_flags = content_flags or {}
        
        # Check for NSFW content routing
        if content_flags.get("nsfw", False):
            nsfw_adapters = [adapter for adapter in self.get_available_adapters() 
                           if self.config["adapters"][adapter].get("content_filtering", {}).get("supports_nsfw", False)]
            if nsfw_adapters:
                return nsfw_adapters[0]
        
        # Check content type specific routing
        if content_type in routing_rules:
            preferred_adapter = routing_rules[content_type]
            if preferred_adapter in self.get_available_adapters():
                return preferred_adapter
        
        # Default routing
        return routing_rules.get("default", self.default_adapter)
    
    def get_fallback_chain(self, adapter_name: str) -> List[str]:
        """Get the fallback chain for a specific adapter."""
        if "fallback_chains" not in self.config:
            return [adapter_name]
        
        return self.config["fallback_chains"].get(adapter_name, [adapter_name])
    
    async def generate_image(self, prompt: str, adapter_name: str = None, **kwargs) -> str:
        """Generate image using specified or default image adapter."""
        # Use image_adapter from config if no adapter specified
        if adapter_name is None:
            adapter_name = self.config.get("image_adapter", "mock_image")
        
        if adapter_name not in self.adapters:
            # Try to initialize the adapter
            if not await self.initialize_adapter(adapter_name):
                raise RuntimeError(f"Failed to initialize image adapter: {adapter_name}")
        
        adapter = self.adapters[adapter_name]
        
        # Check if this is actually an image adapter
        if not hasattr(adapter, 'generate_image'):
            raise RuntimeError(f"Adapter '{adapter_name}' does not support image generation")
        
        return await adapter.generate_image(prompt, **kwargs)

    # ================================
    # DYNAMIC MODEL MANAGEMENT
    # ================================
    
    def add_model_config(self, name: str, config: Dict[str, Any], enabled: bool = True) -> bool:
        """Add a new model configuration dynamically."""
        try:
            # Create model config file
            models_dir = os.path.join("config", "models")
            os.makedirs(models_dir, exist_ok=True)
            
            model_file = os.path.join(models_dir, f"{name}.json")
            
            # Write the individual model config
            with open(model_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            
            # Update registry
            self._update_registry_add_model(name, enabled)
            
            # Reload configuration
            self.config = self._load_config()
            
            log_system_event("dynamic_model_add", f"Added model configuration: {name}")
            return True
            
        except Exception as e:
            log_system_event("dynamic_model_add_error", f"Failed to add model {name}: {e}")
            return False
    
    def remove_model_config(self, name: str) -> bool:
        """Remove a model configuration dynamically."""
        try:
            # Remove from runtime if initialized
            if name in self.adapters:
                del self.adapters[name]
            
            # Remove model config file
            model_file = os.path.join("config", "models", f"{name}.json")
            if os.path.exists(model_file):
                os.remove(model_file)
            
            # Update registry
            self._update_registry_remove_model(name)
            
            # Reload configuration
            self.config = self._load_config()
            
            # Update default adapter if needed
            if self.default_adapter == name:
                available = self.get_available_adapters()
                self.default_adapter = available[0] if available else "mock"
            
            log_system_event("dynamic_model_remove", f"Removed model configuration: {name}")
            return True
            
        except Exception as e:
            log_system_event("dynamic_model_remove_error", f"Failed to remove model {name}: {e}")
            return False
    
    def enable_model(self, name: str) -> bool:
        """Enable a model in the registry."""
        return self._update_registry_enable_model(name, True)
    
    def disable_model(self, name: str) -> bool:
        """Disable a model in the registry."""
        return self._update_registry_enable_model(name, False)
    
    def _update_registry_add_model(self, name: str, enabled: bool = True) -> bool:
        """Add a model to the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            
            # Load existing registry or create new one
            if os.path.exists(registry_file):
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            else:
                registry = {
                    "version": "1.0.0",
                    "models": [],
                    "fallback_chains": {},
                    "content_routing": {}
                }
            
            # Check if model already exists
            existing_model = None
            for model in registry["models"]:
                if model["name"] == name:
                    existing_model = model
                    break
            
            if existing_model:
                # Update existing model
                existing_model["enabled"] = enabled
            else:
                # Add new model
                registry["models"].append({
                    "name": name,
                    "enabled": enabled
                })
            
            # Save updated registry
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            
            return True
            
        except Exception as e:
            log_system_event("registry_update_error", f"Failed to update registry for {name}: {e}")
            return False
    
    def _update_registry_remove_model(self, name: str) -> bool:
        """Remove a model from the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            
            if not os.path.exists(registry_file):
                return True  # Nothing to remove
            
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            # Remove model from registry
            registry["models"] = [model for model in registry["models"] if model["name"] != name]
            
            # Remove from fallback chains
            if "fallback_chains" in registry:
                # Remove as primary adapter
                if name in registry["fallback_chains"]:
                    del registry["fallback_chains"][name]
                
                # Remove from other chains
                for chain_name, chain in registry["fallback_chains"].items():
                    if name in chain:
                        registry["fallback_chains"][chain_name] = [adapter for adapter in chain if adapter != name]
            
            # Remove from content routing
            if "content_routing" in registry:
                for route_type, adapters in registry["content_routing"].items():
                    if isinstance(adapters, list) and name in adapters:
                        registry["content_routing"][route_type] = [adapter for adapter in adapters if adapter != name]
            
            # Save updated registry
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            
            return True
            
        except Exception as e:
            log_system_event("registry_remove_error", f"Failed to remove {name} from registry: {e}")
            return False
    
    def _update_registry_enable_model(self, name: str, enabled: bool) -> bool:
        """Enable or disable a model in the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            
            if not os.path.exists(registry_file):
                return False
            
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            # Find and update the model
            for model in registry["models"]:
                if model["name"] == name:
                    model["enabled"] = enabled
                    break
            else:
                return False  # Model not found
            
            # Save updated registry
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            
            # Reload configuration
            self.config = self._load_config()
            
            # Remove from runtime if disabled
            if not enabled and name in self.adapters:
                del self.adapters[name]
            
            action = "enabled" if enabled else "disabled"
            log_system_event("dynamic_model_toggle", f"Model {name} {action}")
            return True
            
        except Exception as e:
            log_system_event("registry_enable_error", f"Failed to {action} model {name}: {e}")
            return False
    
    def list_model_configs(self) -> Dict[str, Any]:
        """List all model configurations with their status."""
        models_info = {}
        
        # Get registry information
        registry_file = os.path.join("config", "model_registry.json")
        registry_models = {}
        
        if os.path.exists(registry_file):
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
                registry_models = {model["name"]: model["enabled"] for model in registry["models"]}
        
        # Get model file information
        models_dir = os.path.join("config", "models")
        if os.path.exists(models_dir):
            for model_file in os.listdir(models_dir):
                if model_file.endswith(".json"):
                    model_name = model_file[:-5]  # Remove .json extension
                    model_path = os.path.join(models_dir, model_file)
                    
                    try:
                        with open(model_path, "r", encoding="utf-8") as f:
                            model_config = json.load(f)
                        
                        models_info[model_name] = {
                            "type": model_config.get("type", "unknown"),
                            "model_name": model_config.get("api_config", {}).get("model_name", "unknown"),
                            "enabled": registry_models.get(model_name, False),
                            "initialized": model_name in self.adapters,
                            "config_file": model_path
                        }
                    except Exception as e:
                        models_info[model_name] = {
                            "type": "error",
                            "model_name": "unknown",
                            "enabled": False,
                            "initialized": False,
                            "config_file": model_path,
                            "error": str(e)
                        }
        
        return models_info

    async def shutdown(self):
        """Shutdown all adapters."""
        for adapter in self.adapters.values():
            if hasattr(adapter, 'client') and adapter.client:
                if hasattr(adapter.client, 'aclose'):
                    await adapter.client.aclose()

# Global model manager instance
model_manager = ModelManager()

# ================================
# TEXT GENERATION ADAPTERS
# ================================

class AnthropicAdapter(ModelAdapter):
    """Anthropic Claude adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = config.get("base_url", "https://api.anthropic.com")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Anthropic client."""
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("anthropic package required for Anthropic adapter")
        except Exception as e:
            log_error(f"Failed to initialize Anthropic adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Anthropic Claude."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Anthropic model information."""
        return {
            "provider": "Anthropic",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class GeminiAdapter(ModelAdapter):
    """Google Gemini adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("GOOGLE_API_KEY")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Gemini client."""
        if not self.api_key:
            raise ValueError("Google API key required")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("google-generativeai package required for Gemini adapter")
        except Exception as e:
            log_error(f"Failed to initialize Gemini adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Google Gemini."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_output_tokens": kwargs.get("max_tokens", self.max_tokens),
                }
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Gemini model information."""
        return {
            "provider": "Google",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class GroqAdapter(ModelAdapter):
    """Groq fast inference adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("GROQ_API_KEY")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Groq client."""
        if not self.api_key:
            raise ValueError("Groq API key required")
        
        try:
            import groq
            self.client = groq.AsyncGroq(api_key=self.api_key)
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("groq package required for Groq adapter")
        except Exception as e:
            log_error(f"Failed to initialize Groq adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Groq."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Groq API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Groq model information."""
        return {
            "provider": "Groq",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class CohereAdapter(ModelAdapter):
    """Cohere Command adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("COHERE_API_KEY")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Cohere client."""
        if not self.api_key:
            raise ValueError("Cohere API key required")
        
        try:
            import cohere
            self.client = cohere.AsyncClient(api_key=self.api_key)
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("cohere package required for Cohere adapter")
        except Exception as e:
            log_error(f"Failed to initialize Cohere adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Cohere."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.generate(
                model=self.model_name,
                prompt=prompt,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            return response.generations[0].text
        except Exception as e:
            raise RuntimeError(f"Cohere API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Cohere model information."""
        return {
            "provider": "Cohere",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class MistralAdapter(ModelAdapter):
    """Mistral AI adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("MISTRAL_API_KEY")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Mistral client."""
        if not self.api_key:
            raise ValueError("Mistral API key required")
        
        try:
            from mistralai.async_client import MistralAsyncClient
            self.client = MistralAsyncClient(api_key=self.api_key)
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("mistralai package required for Mistral adapter")
        except Exception as e:
            log_error(f"Failed to initialize Mistral adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Mistral."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            from mistralai.models.chat_completion import ChatMessage
            response = await self.client.chat(
                model=self.model_name,
                messages=[ChatMessage(role="user", content=prompt)],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Mistral API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Mistral model information."""
        return {
            "provider": "Mistral",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class HuggingFaceAdapter(ModelAdapter):
    """Hugging Face Inference API adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("HUGGINGFACE_API_KEY")
        self.base_url = config.get("base_url", "https://api-inference.huggingface.co/models/")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Hugging Face client."""
        if not self.api_key:
            raise ValueError("Hugging Face API key required")
        
        try:
            import httpx
            self.client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("httpx package required for Hugging Face adapter")
        except Exception as e:
            log_error(f"Failed to initialize Hugging Face adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Hugging Face."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.post(
                f"{self.base_url}{self.model_name}",
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": kwargs.get("max_tokens", self.max_tokens),
                        "temperature": kwargs.get("temperature", self.temperature)
                    }
                }
            )
            result = response.json()
            return result[0]["generated_text"]
        except Exception as e:
            raise RuntimeError(f"Hugging Face API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Hugging Face model information."""
        return {
            "provider": "Hugging Face",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

class AzureOpenAIAdapter(ModelAdapter):
    """Azure OpenAI adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = config.get("api_version", "2024-02-01")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Azure OpenAI client."""
        if not self.api_key or not self.azure_endpoint:
            raise ValueError("Azure OpenAI API key and endpoint required")
        
        try:
            from openai import AsyncAzureOpenAI
            self.client = AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version
            )
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("openai package required for Azure OpenAI adapter")
        except Exception as e:
            log_error(f"Failed to initialize Azure OpenAI adapter: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Azure OpenAI."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Azure OpenAI API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Azure OpenAI model information."""
        return {
            "provider": "Azure OpenAI",
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "initialized": self.initialized
        }

# ================================
# IMAGE GENERATION ADAPTERS
# ================================

class ImageAdapter(ModelAdapter):
    """Abstract base class for image generation adapters."""
    
    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate an image from a text prompt. Returns base64 or URL."""
        pass
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Redirect to image generation for compatibility."""
        return await self.generate_image(prompt, **kwargs)

class OpenAIImageAdapter(ImageAdapter):
    """OpenAI DALL-E image adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.size = config.get("size", "1024x1024")
        self.quality = config.get("quality", "standard")
        self.style = config.get("style", "vivid")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize OpenAI client."""
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("openai package required for OpenAI image adapter")
        except Exception as e:
            log_error(f"Failed to initialize OpenAI image adapter: {e}")
            return False
    
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate image using DALL-E."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.images.generate(
                model=self.model_name,
                prompt=prompt,
                size=kwargs.get("size", self.size),
                quality=kwargs.get("quality", self.quality),
                style=kwargs.get("style", self.style),
                n=1
            )
            return response.data[0].url
        except Exception as e:
            raise RuntimeError(f"OpenAI Image API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI image model information."""
        return {
            "provider": "OpenAI",
            "model_name": self.model_name,
            "size": self.size,
            "quality": self.quality,
            "style": self.style,
            "initialized": self.initialized
        }

class StabilityAdapter(ImageAdapter):
    """Stability AI Stable Diffusion adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("STABILITY_API_KEY")
        self.width = config.get("width", 1024)
        self.height = config.get("height", 1024)
        self.steps = config.get("steps", 30)
        self.cfg_scale = config.get("cfg_scale", 7)
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Stability client."""
        if not self.api_key:
            raise ValueError("Stability API key required")
        
        try:
            import httpx
            self.client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("httpx package required for Stability adapter")
        except Exception as e:
            log_error(f"Failed to initialize Stability adapter: {e}")
            return False
    
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate image using Stability AI."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.post(
                f"https://api.stability.ai/v1/generation/{self.model_name}/text-to-image",
                json={
                    "text_prompts": [{"text": prompt}],
                    "cfg_scale": kwargs.get("cfg_scale", self.cfg_scale),
                    "height": kwargs.get("height", self.height),
                    "width": kwargs.get("width", self.width),
                    "steps": kwargs.get("steps", self.steps),
                    "samples": 1
                }
            )
            result = response.json()
            return f"data:image/png;base64,{result['artifacts'][0]['base64']}"
        except Exception as e:
            raise RuntimeError(f"Stability API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Stability model information."""
        return {
            "provider": "Stability AI",
            "model_name": self.model_name,
            "width": self.width,
            "height": self.height,
            "steps": self.steps,
            "cfg_scale": self.cfg_scale,
            "initialized": self.initialized
        }

class ReplicateAdapter(ImageAdapter):
    """Replicate API adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("REPLICATE_API_TOKEN")
        self.width = config.get("width", 1024)
        self.height = config.get("height", 1024)
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Replicate client."""
        if not self.api_key:
            raise ValueError("Replicate API token required")
        
        try:
            import replicate
            replicate.api_token = self.api_key
            self.client = replicate
            self.initialized = True
            return True
        except ImportError:
            raise ImportError("replicate package required for Replicate adapter")
        except Exception as e:
            log_error(f"Failed to initialize Replicate adapter: {e}")
            return False
    
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate image using Replicate."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            output = self.client.run(
                self.model_name,
                input={
                    "prompt": prompt,
                    "width": kwargs.get("width", self.width),
                    "height": kwargs.get("height", self.height)
                }
            )
            return output[0] if isinstance(output, list) else output
        except Exception as e:
            raise RuntimeError(f"Replicate API error: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Replicate model information."""
        return {
            "provider": "Replicate",
            "model_name": self.model_name,
            "width": self.width,
            "height": self.height,
            "initialized": self.initialized
        }

class MockImageAdapter(ImageAdapter):
    """Mock image adapter for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.responses = config.get("responses", [
            "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzMzNzNkYyIvPgogIDx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zNWVtIj5Nb2NrIEltYWdlPC90ZXh0Pgo8L3N2Zz4K"
        ])
        self.response_index = 0
    
    async def initialize(self) -> bool:
        """Initialize mock image adapter."""
        self.initialized = True
        return True
    
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate mock image."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        # Cycle through responses
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        
        return response
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get mock image model information."""
        return {
            "provider": "Mock",
            "model_name": self.model_name,
            "responses_count": len(self.responses),
            "current_index": self.response_index,
            "initialized": self.initialized
        }
