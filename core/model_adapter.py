"""
Model adapter system for OpenChronicle.
Provides a unified interface for different LLM backends (OpenAI, Ollama, local models).
"""

import json
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, UTC
from pathlib import Path

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_model_interaction, log_system_event, log_info, log_error

class ModelAdapter(ABC):
    """Abstract base class for model adapters."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get("model_name", "unknown")
        # Only set max_tokens for text models, not image models
        if config.get("type") != "image":
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
    
    def log_interaction(self, story_id: str, prompt: str, response: str, metadata: Optional[Dict[str, Any]] = None):
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
            "timestamp": datetime.now(UTC).isoformat(),
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
    
    def __init__(self, config: Dict[str, Any], model_manager=None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.model_manager = model_manager
        self.base_url = self._get_base_url(config)
        self.client = None
    
    def _get_base_url(self, config: Dict[str, Any]) -> str:
        """Get base URL from config or model manager."""
        # Check explicit config first
        if "base_url" in config:
            return config["base_url"]
        
        # Use model manager if available
        if self.model_manager:
            try:
                return self.model_manager.get_provider_base_url("openai")
            except Exception:
                pass
        
        # Fallback to environment variable only
        env_url = os.getenv("OPENAI_BASE_URL")
        if env_url:
            return env_url
            
        raise ValueError("No base URL configured for OpenAI. Please set OPENAI_BASE_URL or configure in registry.")
    
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
            response = await self.client.chat.completions.create(  # type: ignore
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a creative storytelling assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                stop=kwargs.get("stop_sequences", None)
            )
            
            content = response.choices[0].message.content
            if content is None:
                return ""
            return content.strip()
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
    
    def __init__(self, config: Dict[str, Any], model_manager=None):
        super().__init__(config)
        self.model_manager = model_manager
        self.base_url = self._get_base_url(config)
        self.client = None
    
    def _get_base_url(self, config: Dict[str, Any]) -> str:
        """Get base URL from config or model manager."""
        # Check explicit config first
        if "base_url" in config:
            return config["base_url"]
        
        # Use model manager if available
        if self.model_manager:
            try:
                return self.model_manager.get_provider_base_url("ollama")
            except Exception:
                pass
        
        # Fallback to environment variable only
        env_url = os.getenv("OLLAMA_HOST")
        if env_url:
            return env_url
            
        raise ValueError("No base URL configured for Ollama. Please set OLLAMA_HOST or configure in registry.")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Ollama client."""
        try:
            import httpx
            timeout = self.config.get('timeout', 30.0)
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
            
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
            
            log_info(f"Ollama request: POST {self.base_url}/api/generate with model={self.model_name}")
            response = await self.client.post("/api/generate", json=payload)  # type: ignore
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
        except Exception as e:
            log_error(f"Ollama generation failed - base_url: {self.base_url}, model: {self.model_name}, error: {e}")
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
        self.default_adapter: Optional[str] = None
        self.global_config = self._load_global_config()
        self.config = self._load_config()
    
    def _load_global_config(self) -> Dict[str, Any]:
        """Load global configuration from registry."""
        registry_file = os.path.join("config", "model_registry.json")
        
        if not os.path.exists(registry_file):
            raise FileNotFoundError(f"Model registry not found at {registry_file}. Please ensure the registry exists.")
        
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            return self._process_global_config(registry)
            
        except Exception as e:
            log_error(f"Failed to load global config from registry: {e}")
            raise

    def _process_global_config(self, registry: Dict[str, Any]) -> Dict[str, Any]:
        """Process registry format for global configuration."""
        env_config = registry.get("environment_config", {})
        global_settings = registry.get("global_settings", {})
        defaults = registry.get("defaults", {})
        
        # Build discovery config with environment variable resolution
        providers = env_config.get("providers", {})
        discovery_config = {}
        
        for provider_name, provider_info in providers.items():
            base_url_env = provider_info.get("base_url_env")
            default_base_url = provider_info.get("default_base_url")
            
            discovery_config[provider_name] = {
                "enabled": True,
                "default_base_url": default_base_url,
                "env_var": base_url_env,
                "timeout": provider_info.get("timeout", 30.0),
                "health_check_enabled": provider_info.get("health_check_enabled", True)
            }
            
            # Apply environment variable override
            if base_url_env:
                env_value = os.getenv(base_url_env)
                if env_value:
                    discovery_config[provider_name]["resolved_base_url"] = env_value
                    log_info(f"Using environment override for {provider_name}: {env_value}")
                else:
                    discovery_config[provider_name]["resolved_base_url"] = default_base_url
        
        global_config = {
            "discovery": discovery_config,
            "defaults": {
                "text_model": defaults.get("text_model", "ollama"),
                "analyzer_model": defaults.get("analyzer_model", "ollama"),
                "image_model": defaults.get("image_model", "openai_dalle"),
                "timeout": 30.0,
                "max_tokens": 2048,
                "temperature": 0.7,
                "enable_logging": global_settings.get("enable_logging", True),
                "enable_fallbacks": global_settings.get("enable_fallbacks", True),
                "enable_health_checks": global_settings.get("enable_health_checks", True)
            }
        }
        
        log_system_event("global_config_loaded", "Global configuration loaded from registry")
        return global_config

    def get_provider_base_url(self, provider: str) -> str:
        """Get the base URL for a provider from registry environment config."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            if not os.path.exists(registry_file):
                raise FileNotFoundError(f"Model registry not found at {registry_file}")
            
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            env_config = registry.get("environment_config", {})
            providers = env_config.get("providers", {})
            
            if provider not in providers:
                raise ValueError(f"Provider '{provider}' not found in environment_config")
            
            provider_info = providers[provider]
            base_url_env = provider_info.get("base_url_env")
            default_base_url = provider_info.get("default_base_url")
            
            # Check environment variable first
            if base_url_env:
                env_value = os.getenv(base_url_env)
                if env_value:
                    log_info(f"Using environment override for {provider}: {env_value}")
                    return env_value
            
            # Fall back to default URL from registry
            if default_base_url:
                return default_base_url
            
            raise ValueError(f"No base URL configured for provider '{provider}'")
                        
        except Exception as e:
            log_error(f"Error getting base URL for provider {provider}: {e}")
            raise

    def get_global_default(self, key: str, fallback: Any = None) -> Any:
        """Get a global default configuration value."""
        return self.global_config.get("defaults", {}).get(key, fallback)
    
    def get_intelligent_routing_config(self) -> Dict[str, Any]:
        """Get intelligent routing configuration from the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            if os.path.exists(registry_file):
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                global_settings = registry.get("global_settings", {})
                return global_settings.get("intelligent_routing", {})
                    
        except Exception as e:
            log_error(f"Error getting intelligent routing config: {e}")
        
        return {"enabled": False}
    
    def get_content_routing_config(self) -> Dict[str, Any]:
        """Get content routing configuration from the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            if os.path.exists(registry_file):
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                return registry.get("content_routing", {})
                    
        except Exception as e:
            log_error(f"Error getting content routing config: {e}")
        
        return {}
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance tuning configuration from the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            if os.path.exists(registry_file):
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                return registry.get("performance_tuning", {})
                    
        except Exception as e:
            log_error(f"Error getting performance config: {e}")
        
        return {}
    
    def get_enabled_models_by_type(self, model_type: str = "text") -> List[Dict[str, Any]]:
        """Get all enabled models of a specific type from the registry."""
        enabled_models = []
        
        try:
            registry_file = os.path.join("config", "model_registry.json")
            if os.path.exists(registry_file):
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                if model_type == "text":
                    text_models = registry.get("text_models", {})
                    for priority_group in ["high_priority", "standard_priority", "testing"]:
                        if priority_group in text_models:
                            for model in text_models[priority_group]:
                                if model.get("enabled", True):
                                    enabled_models.append(model)
                elif model_type == "image":
                    image_models = registry.get("image_models", {})
                    for priority_group in ["primary", "testing"]:
                        if priority_group in image_models:
                            for model in image_models[priority_group]:
                                if model.get("enabled", True):
                                    enabled_models.append(model)
                    
        except Exception as e:
            log_error(f"Error getting enabled models: {e}")
        
        return enabled_models

    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from registry."""
        registry_file = os.path.join("config", "model_registry.json")
        
        if not os.path.exists(registry_file):
            raise FileNotFoundError(f"Model registry not found at {registry_file}. Please ensure the registry exists.")
        
        log_system_event("model_config_loading", "Loading model configuration from registry")
        return self._load_plugin_config(registry_file)

    def _load_plugin_config(self, registry_file: str) -> Dict[str, Any]:
        """Load model configuration from registry."""
        log_info("Loading registry model configuration")
        log_system_event("plugin_config_loading", f"Loading registry model configuration from {registry_file}")
        
        # Load the registry
        with open(registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        
        # Get models from hierarchical structure
        all_models = []
        text_models = registry.get("text_models", {})
        image_models = registry.get("image_models", {})
        
        # Collect all text models from different priority groups
        for priority_group in ["high_priority", "standard_priority", "testing"]:
            if priority_group in text_models:
                for model in text_models[priority_group]:
                    model["type"] = "text"  # Ensure type is set
                    all_models.append(model)
        
        # Collect all image models from different priority groups
        for priority_group in ["primary", "testing"]:
            if priority_group in image_models:
                for model in image_models[priority_group]:
                    model["type"] = "image"  # Ensure type is set
                    all_models.append(model)
                    
        log_system_event("plugin_config_registry", f"Loaded registry with {len(all_models)} model entries")
        
        # Build adapters directly from registry entries
        adapters = {}
        
        for model_entry in all_models:
            if not model_entry.get("enabled", True):
                continue
                
            provider = model_entry["name"]
            
            try:
                # Create adapter config directly from registry entry
                adapter_config = {
                    "type": model_entry.get("type", provider),  # Use provider name as type if not specified
                    "model_name": model_entry.get("model_name", provider),
                    "temperature": model_entry.get("temperature", 0.7),
                    "supports_nsfw": model_entry.get("supports_nsfw", False),
                    "content_types": model_entry.get("content_types", ["general"]),
                    "description": model_entry.get("description", f"{provider} model adapter")
                }
                
                # Merge config section if it exists
                if "config" in model_entry:
                    adapter_config.update(model_entry["config"])
                
                # Add max_tokens only for text models, not image models
                if model_entry.get("type") != "image":
                    adapter_config["max_tokens"] = model_entry.get("max_tokens", 2048)
                
                # Add image-specific parameters for image models
                if model_entry.get("type") == "image":
                    if "size" in model_entry:
                        adapter_config["size"] = model_entry["size"]
                    if "quality" in model_entry:
                        adapter_config["quality"] = model_entry["quality"]
                    if "style" in model_entry:
                        adapter_config["style"] = model_entry["style"]
                    if "width" in model_entry:
                        adapter_config["width"] = model_entry["width"]
                    if "height" in model_entry:
                        adapter_config["height"] = model_entry["height"]
                    if "steps" in model_entry:
                        adapter_config["steps"] = model_entry["steps"]
                
                # Add provider-specific configurations
                if provider == "mock":
                    adapter_config["responses"] = [
                        "The story continues with rich detail and engaging narrative.",
                        "Your character moves forward, discovering new possibilities.",
                        "The world around you shifts as the tale unfolds."
                    ]
                elif provider == "mock_image":
                    adapter_config["responses"] = [
                        "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzMzNzNkYyIvPgogIDx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zNWVtIj5Nb2NrIEltYWdlPC90ZXh0Pgo8L3N2Zz4K"
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
        fallback_chains = registry.get("fallback_chains", {})
        
        # Build content routing
        content_routing = {}
        if "content_routing" in registry:
            content_routing = registry["content_routing"]
        else:
            # Create basic content routing from available models
            enabled_models = [m["name"] for m in all_models if m.get("enabled", True)]
            nsfw_models = [m["name"] for m in all_models if m.get("supports_nsfw", False)]
            safe_models = [m["name"] for m in all_models if not m.get("supports_nsfw", False)]
            
            content_routing = {
                "nsfw_content": {
                    "allowed_models": nsfw_models if nsfw_models else ["mock"],
                    "default_model": nsfw_models[0] if nsfw_models else "mock"
                },
                "safe_content": {
                    "allowed_models": safe_models if safe_models else enabled_models,
                    "default_model": safe_models[0] if safe_models else (enabled_models[0] if enabled_models else "mock")
                }
            }
        
        # Determine default adapter from registry format
        default_adapter = "mock"
        if "defaults" in registry:
            default_adapter = registry["defaults"].get("text_model", "mock")
        elif "default_model" in registry:
            default_adapter = registry["default_model"]
        
        # If the default adapter didn't load, find the first available one
        if default_adapter not in adapters:
            if adapters:
                default_adapter = list(adapters.keys())[0]
                log_info(f"Default adapter not available, using '{default_adapter}'")
            else:
                default_adapter = "mock"
                log_info("No adapters loaded, defaulting to mock")
        
        config = {
            "default_adapter": default_adapter,
            "adapters": adapters,
            "fallback_chains": fallback_chains,
            "content_routing": content_routing
        }
        
        log_info(f"Registry-only configuration loaded with {len(adapters)} adapters")
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
                adapter = OpenAIAdapter(adapter_config, self)
            elif adapter_type == "ollama":
                adapter = OllamaAdapter(adapter_config, self)
            elif adapter_type == "mock":
                adapter = MockAdapter(adapter_config)
            elif adapter_type == "anthropic":
                adapter = AnthropicAdapter(adapter_config, self)
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
                adapter = OpenAIImageAdapter(adapter_config, self)
            elif adapter_type == "stability":
                adapter = StabilityAdapter(adapter_config, self)
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
    
    async def generate_response(self, prompt: str, adapter_name: Optional[str] = None, story_id: Optional[str] = None, **kwargs) -> str:
        """Generate response using specified or default adapter with fallback support."""
        adapter_name = adapter_name or self.default_adapter or "mock"
        
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
    
    def get_adapter_for_content(self, content_type: str, content_flags: Optional[Dict[str, Any]] = None) -> str:
        """Get the best adapter for specific content type based on content routing rules."""
        if "content_routing" not in self.config:
            return self.default_adapter or "mock"
        
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
        return routing_rules.get("default", self.default_adapter or "mock")
    
    def get_fallback_chain(self, adapter_name: str) -> List[str]:
        """Get the fallback chain for a specific adapter."""
        if "fallback_chains" not in self.config:
            return [adapter_name]
        
        return self.config["fallback_chains"].get(adapter_name, [adapter_name])
    
    async def generate_image(self, prompt: str, adapter_name: Optional[str] = None, **kwargs) -> str:
        """Generate image using specified or default image adapter."""
        # Use image_adapter from config if no adapter specified
        if adapter_name is None:
            adapter_name = self.config.get("image_adapter", "mock_image")
        
        # At this point adapter_name is guaranteed to be a string
        assert adapter_name is not None  # Type hint for VS Code
        
        if adapter_name not in self.adapters:
            # Try to initialize the adapter
            if not await self.initialize_adapter(adapter_name):
                raise RuntimeError(f"Failed to initialize image adapter: {adapter_name}")
        
        adapter = self.adapters[adapter_name]
        
        # Check if this is actually an image adapter
        if not hasattr(adapter, 'generate_image'):
            raise RuntimeError(f"Adapter '{adapter_name}' does not support image generation")
        
        # Type assertion for VS Code
        assert isinstance(adapter, ImageAdapter), f"Adapter {adapter_name} is not an image adapter"
        return await adapter.generate_image(prompt, **kwargs)

    # ================================
    # DYNAMIC MODEL MANAGEMENT
    # ================================
    
    def add_model_config(self, name: str, config: Dict[str, Any], enabled: bool = True) -> bool:
        """Add a new model configuration dynamically to the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            
            # Load existing registry or create new one
            if os.path.exists(registry_file):
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            else:
                # Create a basic registry structure
                registry = {
                    "metadata": {
                        "name": "OpenChronicle Model Registry",
                        "description": "Centralized configuration for all AI models and providers",
                        "maintainer": "OpenChronicle Team"
                    },
                    "defaults": {
                        "text_model": "mock",
                        "image_model": "mock_image"
                    },
                    "text_models": {
                        "testing": []
                    },
                    "image_models": {
                        "testing": []
                    },
                    "content_routing": {
                        "nsfw_content": {"allowed_models": ["mock"], "default_model": "mock"},
                        "safe_content": {"allowed_models": ["mock"], "default_model": "mock"}
                    },
                    "fallback_chains": {
                        "mock": ["mock"]
                    }
                }
            
            # Prepare model entry
            model_entry = {
                "name": name,
                "enabled": enabled,
                **config  # Include all config fields in the model entry
            }
            
            # Determine if this is a text or image model
            model_type = config.get("type", "text")
            is_image_model = (model_type == "image" or 
                            name.endswith("_image") or 
                            name.endswith("_dalle") or 
                            "image" in config.get("content_types", []))
            
            # Add to appropriate section
            if is_image_model:
                if "image_models" not in registry:
                    registry["image_models"] = {"testing": []}
                if "testing" not in registry["image_models"]:
                    registry["image_models"]["testing"] = []
                
                # Check if model already exists
                existing_models = registry["image_models"]["testing"]
                for i, existing_model in enumerate(existing_models):
                    if existing_model["name"] == name:
                        existing_models[i] = model_entry
                        break
                else:
                    registry["image_models"]["testing"].append(model_entry)
            else:
                # Text model
                if "text_models" not in registry:
                    registry["text_models"] = {"testing": []}
                if "testing" not in registry["text_models"]:
                    registry["text_models"]["testing"] = []
                
                # Check if model already exists
                existing_models = registry["text_models"]["testing"]
                for i, existing_model in enumerate(existing_models):
                    if existing_model["name"] == name:
                        existing_models[i] = model_entry
                        break
                else:
                    registry["text_models"]["testing"].append(model_entry)
            
            # Save updated registry
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            
            # Reload configuration
            self.config = self._load_config()
            
            log_system_event("dynamic_model_add", f"Added model configuration: {name}")
            return True
            
        except Exception as e:
            log_system_event("dynamic_model_add_error", f"Failed to add model {name}: {e}")
            return False
    
    def remove_model_config(self, name: str) -> bool:
        """Remove a model configuration dynamically from the registry."""
        try:
            # Remove from runtime if initialized
            if name in self.adapters:
                del self.adapters[name]
            
            # Update registry
            registry_file = os.path.join("config", "model_registry.json")
            
            if not os.path.exists(registry_file):
                return True  # Nothing to remove
            
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            # Remove from text_models and image_models
            model_removed = False
            
            # Check text models
            text_models = registry.get("text_models", {})
            for priority_group in ["high_priority", "standard_priority", "testing"]:
                if priority_group in text_models:
                    original_count = len(text_models[priority_group])
                    text_models[priority_group] = [
                        model for model in text_models[priority_group] 
                        if model["name"] != name
                    ]
                    if len(text_models[priority_group]) < original_count:
                        model_removed = True
            
            # Check image models
            image_models = registry.get("image_models", {})
            for priority_group in ["primary", "testing"]:
                if priority_group in image_models:
                    original_count = len(image_models[priority_group])
                    image_models[priority_group] = [
                        model for model in image_models[priority_group] 
                        if model["name"] != name
                    ]
                    if len(image_models[priority_group]) < original_count:
                        model_removed = True
            
            # Remove from fallback chains
            if "fallback_chains" in registry:
                for chain_name, chain in registry["fallback_chains"].items():
                    if isinstance(chain, list) and name in chain:
                        registry["fallback_chains"][chain_name] = [
                            adapter for adapter in chain if adapter != name
                        ]
            
            # Remove from content routing
            if "content_routing" in registry:
                for route_type, route_config in registry["content_routing"].items():
                    if isinstance(route_config, dict):
                        if "allowed_models" in route_config and isinstance(route_config["allowed_models"], list):
                            if name in route_config["allowed_models"]:
                                route_config["allowed_models"] = [
                                    model for model in route_config["allowed_models"] if model != name
                                ]
                        if route_config.get("default_model") == name:
                            # Set to first available model or mock
                            if route_config["allowed_models"]:
                                route_config["default_model"] = route_config["allowed_models"][0]
                            else:
                                route_config["default_model"] = "mock"
            
            # Save updated registry if a model was actually removed
            if model_removed:
                with open(registry_file, "w", encoding="utf-8") as f:
                    json.dump(registry, f, indent=2)
                
                # Reload configuration
                self.config = self._load_config()
                
                # Update default adapter if needed
                if self.default_adapter == name:
                    available = self.get_available_adapters()
                    self.default_adapter = available[0] if available else "mock"
                
                log_system_event("dynamic_model_remove", f"Removed model configuration: {name}")
            else:
                log_system_event("dynamic_model_remove", f"Model {name} not found in registry")
                
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
    
    def _update_registry_enable_model(self, name: str, enabled: bool) -> bool:
        """Enable or disable a model in the registry."""
        try:
            registry_file = os.path.join("config", "model_registry.json")
            
            if not os.path.exists(registry_file):
                return False
            
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            # Search in text_models and image_models
            model_found = False
            
            # Check text models
            text_models = registry.get("text_models", {})
            for priority_group in ["high_priority", "standard_priority", "testing"]:
                if priority_group in text_models:
                    for model in text_models[priority_group]:
                        if model["name"] == name:
                            model["enabled"] = enabled
                            model_found = True
                            break
                    if model_found:
                        break
            
            # Check image models if not found in text
            if not model_found:
                image_models = registry.get("image_models", {})
                for priority_group in ["primary", "testing"]:
                    if priority_group in image_models:
                        for model in image_models[priority_group]:
                            if model["name"] == name:
                                model["enabled"] = enabled
                                model_found = True
                                break
                        if model_found:
                            break
            
            if not model_found:
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
            action = "enabled" if enabled else "disabled"
            log_system_event("registry_enable_error", f"Failed to {action} model {name}: {e}")
            return False
    
    def list_model_configs(self) -> Dict[str, Any]:
        """List all model configurations with their status from the registry."""
        models_info = {}
        
        # Get registry information
        registry_file = os.path.join("config", "model_registry.json")
        
        if os.path.exists(registry_file):
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                # Collect all models from registry structure
                all_models = []
                
                # Collect text models from different priority groups
                text_models = registry.get("text_models", {})
                for priority_group in ["high_priority", "standard_priority", "testing"]:
                    if priority_group in text_models:
                        for model in text_models[priority_group]:
                            model["type"] = "text"  # Ensure type is set
                            all_models.append(model)
                
                # Collect image models from different priority groups
                image_models = registry.get("image_models", {})
                for priority_group in ["primary", "testing"]:
                    if priority_group in image_models:
                        for model in image_models[priority_group]:
                            model["type"] = "image"  # Ensure type is set
                            all_models.append(model)
                
                for model_entry in all_models:
                    model_name = model_entry["name"]
                    models_info[model_name] = {
                        "type": model_entry.get("type", "text"),
                        "provider": model_entry.get("provider", model_name),
                        "model_name": model_entry.get("model_name", model_name),
                        "enabled": model_entry.get("enabled", False),
                        "initialized": model_name in self.adapters,
                        "supports_nsfw": model_entry.get("supports_nsfw", False),
                        "content_types": model_entry.get("content_types", ["general"]),
                        "description": model_entry.get("description", f"{model_name} model adapter"),
                        "priority": model_entry.get("priority", 99),
                        "fallbacks": model_entry.get("fallbacks", [])
                    }
                    
            except Exception as e:
                log_error(f"Failed to read registry: {e}")
                models_info["error"] = {
                    "type": "error",
                    "error": f"Failed to read registry: {e}"
                }
        else:
            models_info["error"] = {
                "type": "error", 
                "error": "Model registry not found"
            }
        
        return models_info

    async def discover_ollama_models(self, base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Discover available Ollama models by querying the /api/tags endpoint.
        
        Args:
            base_url: Ollama server base URL (optional, uses config if not provided)
            
        Returns:
            Dictionary with discovered models and metadata
        """
        # Use provided URL or get from configuration
        if base_url is None:
            base_url = self.get_provider_base_url("ollama")
            if not base_url:
                return {"error": "No Ollama base URL configured. Set OLLAMA_HOST environment variable or update registry."}
        
        # Get timeout from global config
        timeout = self.global_config.get("discovery", {}).get("ollama", {}).get("timeout", 10.0)
        
        try:
            import httpx
            
            log_info(f"Discovering Ollama models at {base_url} (timeout: {timeout}s)")
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{base_url}/api/tags")
                response.raise_for_status()
                
                data = response.json()
                models = data.get("models", [])
                
                discovered = {
                    "server_url": base_url,
                    "total_models": len(models),
                    "models": {},
                    "timestamp": datetime.now(UTC).isoformat(),
                    "config_source": "environment" if base_url == self.get_provider_base_url("ollama") else "parameter"
                }
                
                for model in models:
                    model_name = model.get("name", "unknown")
                    size_bytes = model.get("size", 0)
                    modified_at = model.get("modified_at", "")
                    
                    # Convert size to human readable
                    if size_bytes > 1024**3:  # GB
                        size_str = f"{size_bytes / (1024**3):.1f} GB"
                    elif size_bytes > 1024**2:  # MB
                        size_str = f"{size_bytes / (1024**2):.1f} MB"
                    else:
                        size_str = f"{size_bytes} bytes"
                    
                    # Extract base model name (remove tags like :latest, :7b, etc.)
                    base_name = model_name.split(":")[0] if ":" in model_name else model_name
                    
                    discovered["models"][model_name] = {
                        "name": model_name,
                        "base_name": base_name,
                        "size": size_bytes,
                        "size_human": size_str,
                        "modified_at": modified_at,
                        "family": self._guess_model_family(base_name),
                        "capabilities": self._guess_model_capabilities(model_name)
                    }
                
                log_system_event("ollama_discovery", f"Discovered {len(models)} Ollama models from {base_url}")
                return discovered
                
        except ImportError:
            error_msg = "httpx package required for Ollama model discovery"
            log_error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Failed to discover Ollama models from {base_url}: {e}"
            log_error(error_msg)
            return {"error": error_msg}

    def _guess_model_family(self, model_name: str) -> str:
        """Guess the model family based on the model name."""
        model_lower = model_name.lower()
        
        # Check more specific models first
        if "codellama" in model_lower:
            return "codellama"
        elif "llama" in model_lower:
            return "llama"
        elif "gemma" in model_lower:
            return "gemma"
        elif "mistral" in model_lower:
            return "mistral"
        elif "phi" in model_lower:
            return "phi"
        elif "qwen" in model_lower:
            return "qwen"
        elif "neural" in model_lower:
            return "neural-chat"
        elif "orca" in model_lower:
            return "orca"
        elif "vicuna" in model_lower:
            return "vicuna"
        else:
            return "unknown"

    def _guess_model_capabilities(self, model_name: str) -> Dict[str, bool]:
        """Guess model capabilities based on the model name."""
        model_lower = model_name.lower()
        
        capabilities = {
            "text_generation": True,  # All models can generate text
            "code_generation": False,
            "instruction_following": False,
            "conversation": False,
            "analysis": False
        }
        
        # Code generation models
        if any(term in model_lower for term in ["code", "coder", "starcoder", "deepseek-coder"]):
            capabilities["code_generation"] = True
        
        # Instruction following models (check for instruct, chat, it)
        if any(term in model_lower for term in ["instruct", "chat", "it"]):
            capabilities["instruction_following"] = True
            capabilities["conversation"] = True
        
        # Analysis capable models (larger models typically better at analysis)
        if any(term in model_lower for term in ["13b", "30b", "70b", "8x7b", "gemma", "llama"]):
            capabilities["analysis"] = True
        
        return capabilities

    async def add_discovered_ollama_models(
        self, 
        base_url: Optional[str] = None,
        auto_enable: bool = True,
        priority_start: int = 10
    ) -> Dict[str, Any]:
        """
        Discover Ollama models and add them to the model registry.
        
        Args:
            base_url: Ollama server base URL (optional, uses config if not provided)
            auto_enable: Whether to enable discovered models by default
            priority_start: Starting priority number for discovered models
            
        Returns:
            Dictionary with results of the discovery and addition process
        """
        discovery_result = await self.discover_ollama_models(base_url)
        
        if "error" in discovery_result:
            return discovery_result
        
        # Get the actual base URL used for discovery
        actual_base_url = discovery_result["server_url"]
        
        results = {
            "discovered_count": discovery_result["total_models"],
            "added_models": [],
            "skipped_models": [],
            "errors": [],
            "base_url": actual_base_url,
            "config_source": discovery_result.get("config_source", "unknown")
        }
        
        # Load current registry
        registry_file = os.path.join("config", "model_registry.json")
        if not os.path.exists(registry_file):
            results["errors"].append("Model registry not found")
            return results
        
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception as e:
            results["errors"].append(f"Failed to load registry: {e}")
            return results
        
        # Check existing models to avoid duplicates
        existing_ollama_models = set()
        
        # Check for existing Ollama models in registry
        text_models = registry.get("text_models", {})
        for priority_group in ["high_priority", "standard_priority", "testing"]:
            if priority_group in text_models:
                for model_entry in text_models[priority_group]:
                    if (model_entry.get("provider") == "ollama" or 
                        model_entry["name"].startswith("ollama_")):
                        model_name = model_entry.get("model_name", "")
                        if model_name:
                            existing_ollama_models.add(model_name)
        
        current_priority = priority_start
        
        # Get global defaults
        default_timeout = self.get_global_default("timeout", 120)
        default_max_tokens = self.get_global_default("max_tokens", 2048)
        default_temperature = self.get_global_default("temperature", 0.7)
        
        # Add each discovered model to registry
        for model_name, model_info in discovery_result["models"].items():
            if model_name in existing_ollama_models:
                results["skipped_models"].append({
                    "name": model_name,
                    "reason": "Already exists in registry"
                })
                continue
            
            # Create registry entry for the model
            registry_name = f"ollama_{model_info['base_name']}_{model_name.split(':')[-1] if ':' in model_name else 'latest'}"
            
            new_model_entry = {
                "name": registry_name,
                "provider": "ollama",
                "enabled": auto_enable,
                "priority": current_priority,
                "model_name": model_name,
                "supports_nsfw": True,  # Ollama models typically support NSFW
                "content_types": ["general", "fantasy", "sci-fi", "creative"],
                "description": f"Ollama {model_info['family']} model - {model_info['size_human']}",
                "fallbacks": ["mock"],
                "config": {
                    "base_url": actual_base_url,
                    "timeout": default_timeout,
                    "max_tokens": default_max_tokens,
                    "temperature": default_temperature
                },
                "metadata": {
                    "family": model_info["family"],
                    "size": model_info["size"],
                    "capabilities": model_info["capabilities"],
                    "discovered_at": discovery_result["timestamp"],
                    "config_source": discovery_result.get("config_source", "unknown")
                }
            }
            
            # Add enhanced content types based on capabilities
            if model_info["capabilities"]["code_generation"]:
                new_model_entry["content_types"].extend(["code", "technical"])
            
            if model_info["capabilities"]["analysis"]:
                new_model_entry["content_types"].append("analysis")
            
            # Add to text_models testing section
            if "text_models" not in registry:
                registry["text_models"] = {"testing": []}
            if "testing" not in registry["text_models"]:
                registry["text_models"]["testing"] = []
            
            registry["text_models"]["testing"].append(new_model_entry)
            
            results["added_models"].append({
                "registry_name": registry_name,
                "model_name": model_name,
                "family": model_info["family"],
                "size": model_info["size_human"],
                "capabilities": model_info["capabilities"]
            })
            
            current_priority += 1
        
        # Save updated registry
        try:
            # Create backup
            backup_file = f"{registry_file}.backup.{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            with open(registry_file, "r", encoding="utf-8") as f:
                backup_content = f.read()
            with open(backup_file, "w", encoding="utf-8") as f:
                f.write(backup_content)
            
            # Write updated registry
            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            
            log_system_event(
                "ollama_models_added", 
                f"Added {len(results['added_models'])} Ollama models to registry from {actual_base_url}"
            )
            
            # Reload configuration to pick up new models
            self.global_config = self._load_global_config()
            self.config = self._load_config()
            
        except Exception as e:
            results["errors"].append(f"Failed to save registry: {e}")
        
        return results

    async def shutdown(self):
        """Shutdown all adapters."""
        for adapter in self.adapters.values():
            # Use getattr with default to avoid type checker issues
            client = getattr(adapter, 'client', None)
            if client:
                if hasattr(client, 'aclose'):
                    await client.aclose()  # type: ignore

# Global model manager instance
model_manager = ModelManager()

# ================================
# TEXT GENERATION ADAPTERS
# ================================

class AnthropicAdapter(ModelAdapter):
    """Anthropic Claude adapter."""
    
    def __init__(self, config: Dict[str, Any], model_manager=None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.model_manager = model_manager
        self.base_url = self._get_base_url(config)
        self.client = None
    
    def _get_base_url(self, config: Dict[str, Any]) -> str:
        """Get base URL from config or model manager."""
        # Check explicit config first
        if "base_url" in config:
            return config["base_url"]
        
        # Use model manager if available
        if self.model_manager:
            try:
                return self.model_manager.get_provider_base_url("anthropic")
            except Exception:
                pass
        
        # Fallback to environment variable only
        env_url = os.getenv("ANTHROPIC_BASE_URL")
        if env_url:
            return env_url
            
        raise ValueError("No base URL configured for Anthropic. Please set ANTHROPIC_BASE_URL or configure in registry.")
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
            response = await self.client.messages.create(  # type: ignore
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            # Handle response content properly for Anthropic
            if hasattr(response, 'content') and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, 'text'):
                    return content_block.text  # type: ignore
            return ""
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
            response = self.client.generate_content(  # type: ignore
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
            response = await self.client.chat.completions.create(  # type: ignore
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            content = response.choices[0].message.content
            if content is None:
                return ""
            return content
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
            response = await self.client.generate(  # type: ignore
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
            response = await self.client.chat(  # type: ignore
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
            response = await self.client.post(  # type: ignore[attr-defined]
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
            response = await self.client.chat.completions.create(  # type: ignore
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            content = response.choices[0].message.content
            if content is None:
                return ""
            return content
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
    
    def __init__(self, config: Dict[str, Any], model_manager=None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.model_manager = model_manager
        self.base_url = self._get_base_url(config)
        self.size = config.get("size", "1024x1024")
        self.quality = config.get("quality", "standard")
        self.style = config.get("style", "vivid")
        self.client = None
    
    def _get_base_url(self, config: Dict[str, Any]) -> str:
        """Get base URL from config or model manager."""
        # Check explicit config first
        if "base_url" in config:
            return config["base_url"]
        
        # Use model manager if available
        if self.model_manager:
            try:
                return self.model_manager.get_provider_base_url("openai")
            except Exception:
                pass
        
        # Fallback to environment variable only
        env_url = os.getenv("OPENAI_BASE_URL")
        if env_url:
            return env_url
            
        raise ValueError("No base URL configured for OpenAI. Please set OPENAI_BASE_URL or configure in registry.")
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
            response = await self.client.images.generate(  # type: ignore
                model=self.model_name,
                prompt=prompt,
                size=kwargs.get("size", self.size),
                quality=kwargs.get("quality", self.quality),
                style=kwargs.get("style", self.style),
                n=1
            )
            if response and response.data and len(response.data) > 0:
                url = response.data[0].url
                if url is None:
                    return ""
                return str(url)
            return ""
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
    
    def __init__(self, config: Dict[str, Any], model_manager=None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("STABILITY_API_KEY")
        self.model_manager = model_manager
        self.base_url = self._get_base_url(config)
        self.width = config.get("width", 1024)
        self.height = config.get("height", 1024)
        self.steps = config.get("steps", 30)
        self.cfg_scale = config.get("cfg_scale", 7)
        self.client = None
    
    def _get_base_url(self, config: Dict[str, Any]) -> str:
        """Get base URL from config or model manager."""
        # Check explicit config first
        if "base_url" in config:
            return config["base_url"]
        
        # Use model manager if available
        if self.model_manager:
            try:
                return self.model_manager.get_provider_base_url("stability")
            except Exception:
                pass
        
        # Fallback to environment variable only
        env_url = os.getenv("STABILITY_BASE_URL")
        if env_url:
            return env_url
            
        raise ValueError("No base URL configured for Stability. Please set STABILITY_BASE_URL or configure in registry.")
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
            response = await self.client.post(  # type: ignore
                f"{self.base_url}/generation/{self.model_name}/text-to-image",
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
            output = self.client.run(  # type: ignore
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
