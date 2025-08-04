#!/usr/bin/env python3
"""
Phase 3.0 Day 4: ConfigurationManager Component

Extracted from ModelManager to handle configuration management, registry operations,
and dynamic model configuration. Provides clean separation of concerns for all
configuration-related functionality with comprehensive validation and management.

File: core/model_management/configuration_manager.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Import system components
from utilities.logging_system import log_info, log_error, log_warning, log_system_event

UTC = timezone.utc


class ConfigurationManager:
    """
    Manages configuration loading, validation, and dynamic updates.
    
    Extracted from ModelManager to provide focused responsibility for configuration
    management with clean interfaces and comprehensive validation capabilities.
    """
    
    def __init__(self, config_path: str = "config"):
        """
        Initialize the ConfigurationManager.
        
        Args:
            config_path: Base path for configuration files
        """
        self.config_path = Path(config_path)
        self.registry_file = self.config_path / "model_registry.json"
        self.runtime_state_file = self.config_path / "model_runtime_state.json"
        
        # Configuration state
        self.registry = {}
        self.global_config = {}
        self.config = {}
        
        # Load initial configuration
        self._initialize_configuration()
        
        log_system_event("configuration_manager_initialized", "Configuration management system ready")
    
    def _initialize_configuration(self):
        """Initialize configuration management system."""
        try:
            # Load global configuration
            self.global_config = self._load_global_config()
            
            # Load full registry
            self.registry = self._load_full_registry()
            
            # Load plugin configuration
            self.config = self._load_config()
            
            log_system_event("configuration_initialized", "Configuration system initialized successfully")
            
        except Exception as e:
            log_error(f"Failed to initialize configuration: {e}")
            # Create minimal fallback configuration
            self._create_fallback_configuration()
    
    def _load_global_config(self) -> Dict[str, Any]:
        """Load global configuration from registry."""
        if not self.registry_file.exists():
            raise FileNotFoundError(f"Model registry not found at {self.registry_file}. Please ensure the registry exists.")
        
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            return self._process_global_config(registry)
            
        except Exception as e:
            log_error(f"Failed to load global config from registry: {e}")
            raise
    
    def _load_full_registry(self) -> Dict[str, Any]:
        """Load the complete registry for checking disabled adapters."""
        if not self.registry_file.exists():
            return {}
        
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Failed to load full registry: {e}")
            return {}
    
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
                "enable_intelligent_routing": global_settings.get("enable_intelligent_routing", True),
                "enable_content_routing": global_settings.get("enable_content_routing", True),
                "max_concurrent_requests": global_settings.get("max_concurrent_requests", 10),
                "request_timeout": 30.0
            },
            "intelligent_routing": global_settings.get("intelligent_routing", {}),
            "content_routing": registry.get("content_routing", {}),
            "performance_tuning": registry.get("performance_tuning", {}),
            "fallback_chains": registry.get("fallback_chains", {})
        }
        
        return global_config
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from registry."""
        if not self.registry_file.exists():
            raise FileNotFoundError(f"Model registry not found at {self.registry_file}. Please ensure the registry exists.")
        
        log_system_event("model_config_loading", "Loading model configuration from registry")
        return self._load_plugin_config(str(self.registry_file))
    
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
        
        # Build adapters configuration from registry entries
        adapters = {}
        
        for model_entry in all_models:
            if not model_entry.get("enabled", True):
                continue
                
            provider = model_entry["name"]
            
            # PRODUCTION SAFETY: Auto-disable mock adapters in production
            if provider in ["mock", "mock_image"]:
                # Check if we're in a testing environment
                is_testing = (
                    os.getenv("TESTING", "").lower() in ["true", "1", "yes"] or
                    os.getenv("PYTEST_CURRENT_TEST") is not None or
                    "pytest" in sys.modules or
                    "test" in sys.argv[0].lower()
                )
                
                if not is_testing:
                    log_system_event("production_safety", 
                                   f"Auto-disabling {provider} adapter - mock adapters not available in production")
                    continue  # Skip mock adapters in production
            
            try:
                # Create adapter config directly from registry entry
                actual_type = model_entry.get("type")
                if actual_type in ["text", "image"]:
                    # These are category types, not adapter types - use provider name instead
                    actual_type = provider
                elif actual_type is None:
                    actual_type = provider
                
                adapters[provider] = {
                    "type": actual_type,
                    "enabled": True,
                    **{k: v for k, v in model_entry.items() if k not in ["name", "enabled"]}
                }
                
            except Exception as e:
                log_error(f"Error processing model entry {provider}: {e}")
        
        return {"adapters": adapters}
    
    def _create_fallback_configuration(self):
        """Create minimal fallback configuration when loading fails."""
        self.global_config = {
            "discovery": {},
            "defaults": {
                "text_model": "mock",
                "analyzer_model": "mock", 
                "image_model": "mock_image",
                "timeout": 30.0,
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "intelligent_routing": {},
            "content_routing": {},
            "performance_tuning": {},
            "fallback_chains": {}
        }
        
        self.registry = {}
        self.config = {"adapters": {}}
        
        log_warning("Created fallback configuration due to loading errors")
    
    def get_global_default(self, key: str, fallback: Any = None) -> Any:
        """Get a global default configuration value."""
        return self.global_config.get("defaults", {}).get(key, fallback)
    
    def get_intelligent_routing_config(self) -> Dict[str, Any]:
        """Get intelligent routing configuration from the registry."""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                global_settings = registry.get("global_settings", {})
                return global_settings.get("intelligent_routing", {})
                
        except Exception as e:
            log_error(f"Error getting intelligent routing config: {e}")
        
        return {"enabled": False}
    
    def get_content_routing_config(self) -> Dict[str, Any]:
        """Get content routing configuration from the registry."""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                return registry.get("content_routing", {})
                
        except Exception as e:
            log_error(f"Error getting content routing config: {e}")
        
        return {}
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance tuning configuration from the registry."""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                return registry.get("performance_tuning", {})
                
        except Exception as e:
            log_error(f"Error getting performance config: {e}")
        
        return {}
    
    def get_enabled_models_by_type(self, model_type: str = "text") -> List[Dict[str, Any]]:
        """Get all enabled models of a specific type from the registry."""
        enabled_models = []
        
        try:
            if self.registry_file.exists():
                with open(self.registry_file, "r", encoding="utf-8") as f:
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
    
    def add_model_config(self, name: str, config: Dict[str, Any], enabled: bool = True) -> bool:
        """Add a new model configuration dynamically to the registry."""
        try:
            # Load existing registry or create new one
            if self.registry_file.exists():
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            else:
                # Create a basic registry structure
                registry = self._create_basic_registry_structure()
            
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
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            
            # Reload configuration
            self._reload_configuration()
            
            log_system_event("dynamic_model_add", f"Added model configuration: {name}")
            return True
            
        except Exception as e:
            log_system_event("dynamic_model_add_error", f"Failed to add model {name}: {e}")
            return False
    
    def remove_model_config(self, name: str) -> bool:
        """Remove a model configuration dynamically from the registry."""
        try:
            if not self.registry_file.exists():
                return True  # Nothing to remove
            
            with open(self.registry_file, "r", encoding="utf-8") as f:
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
                with open(self.registry_file, "w", encoding="utf-8") as f:
                    json.dump(registry, f, indent=2)
                
                # Reload configuration
                self._reload_configuration()
                
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
            if not self.registry_file.exists():
                return False
            
            with open(self.registry_file, "r", encoding="utf-8") as f:
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
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            
            # Reload configuration
            self._reload_configuration()
            
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
        
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
                # Collect all models from registry structure
                all_models = []
                
                # Collect text models from different priority groups
                text_models = registry.get("text_models", {})
                for priority_group in ["high_priority", "standard_priority", "testing"]:
                    if priority_group in text_models:
                        for model in text_models[priority_group]:
                            model["category"] = "text"
                            model["priority"] = priority_group
                            all_models.append(model)
                
                # Collect image models from different priority groups
                image_models = registry.get("image_models", {})
                for priority_group in ["primary", "testing"]:
                    if priority_group in image_models:
                        for model in image_models[priority_group]:
                            model["category"] = "image"
                            model["priority"] = priority_group
                            all_models.append(model)
                
                # Build models info
                for model in all_models:
                    name = model["name"]
                    models_info[name] = {
                        "type": model.get("type", model.get("category", "unknown")),
                        "enabled": model.get("enabled", True),
                        "category": model.get("category", "unknown"),
                        "priority": model.get("priority", "unknown"),
                        "provider": model.get("provider", name),
                        "model_name": model.get("model_name", ""),
                        "capabilities": model.get("capabilities", []),
                        "config": {k: v for k, v in model.items() 
                                 if k not in ["name", "enabled", "category", "priority"]}
                    }
                
            except Exception as e:
                log_error(f"Error listing model configs: {e}")
        
        return models_info
    
    def validate_model_config(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a model configuration."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            # Check required fields
            required_fields = ["type"]
            for field in required_fields:
                if field not in config:
                    validation_result["errors"].append(f"Missing required field: {field}")
                    validation_result["valid"] = False
            
            # Validate model type
            valid_types = ["text", "image", "openai", "anthropic", "ollama", "groq", "gemini", "cohere", "mistral", "transformers"]
            if "type" in config and config["type"] not in valid_types:
                validation_result["warnings"].append(f"Unknown model type: {config['type']}. Valid types: {valid_types}")
            
            # Check for common configuration issues
            if "api_key" in config and len(config["api_key"]) < 10:
                validation_result["warnings"].append("API key appears to be too short")
            
            if "timeout" in config:
                try:
                    timeout = float(config["timeout"])
                    if timeout < 1 or timeout > 300:
                        validation_result["warnings"].append("Timeout should be between 1 and 300 seconds")
                except (ValueError, TypeError):
                    validation_result["errors"].append("Timeout must be a number")
                    validation_result["valid"] = False
            
            if "max_tokens" in config:
                try:
                    max_tokens = int(config["max_tokens"])
                    if max_tokens < 1 or max_tokens > 100000:
                        validation_result["warnings"].append("max_tokens should be between 1 and 100000")
                except (ValueError, TypeError):
                    validation_result["errors"].append("max_tokens must be an integer")
                    validation_result["valid"] = False
            
            # Add recommendations
            if "provider" not in config:
                validation_result["recommendations"].append("Consider adding 'provider' field for better organization")
            
            if "capabilities" not in config:
                validation_result["recommendations"].append("Consider adding 'capabilities' field to describe model abilities")
                
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {e}")
        
        return validation_result
    
    def get_base_url_for_provider(self, provider: str) -> Optional[str]:
        """Get base URL for a provider from configuration."""
        try:
            provider_config = self.global_config.get("discovery", {}).get(provider, {})
            
            # Return resolved URL if available, otherwise default
            return provider_config.get("resolved_base_url", provider_config.get("default_base_url"))
            
        except Exception as e:
            log_error(f"Error getting base URL for provider {provider}: {e}")
            return None
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """Get fallback chain for a model."""
        fallback_chains = self.global_config.get("fallback_chains", {})
        return fallback_chains.get(model_name, [model_name])
    
    def reload_configuration(self) -> bool:
        """Reload all configuration from files."""
        try:
            self._reload_configuration()
            log_system_event("configuration_reloaded", "Configuration reloaded successfully")
            return True
        except Exception as e:
            log_error(f"Failed to reload configuration: {e}")
            return False
    
    def _reload_configuration(self):
        """Internal method to reload configuration."""
        self.global_config = self._load_global_config()
        self.registry = self._load_full_registry()
        self.config = self._load_config()
    
    def _create_basic_registry_structure(self) -> Dict[str, Any]:
        """Create a basic registry structure for new registries."""
        return {
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
    
    def export_configuration(self, output_file: Optional[str] = None) -> str:
        """Export current configuration to a file."""
        try:
            export_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "global_config": self.global_config,
                "registry": self.registry,
                "config": self.config
            }
            
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"config_export_{timestamp}.json"
            
            export_path = Path(output_file)
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            
            log_system_event("configuration_exported", f"Configuration exported to {export_path}")
            return str(export_path)
            
        except Exception as e:
            log_error(f"Failed to export configuration: {e}")
            raise
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        try:
            adapters_config = self.config.get("adapters", {})
            
            summary = {
                "total_models": len(adapters_config),
                "enabled_models": len([name for name, config in adapters_config.items() 
                                     if config.get("enabled", True)]),
                "text_models": len([name for name, config in adapters_config.items() 
                                  if config.get("type", "text") == "text"]),
                "image_models": len([name for name, config in adapters_config.items() 
                                   if config.get("type") == "image"]),
                "providers": list(set(config.get("provider", config.get("type", "unknown")) 
                                    for config in adapters_config.values())),
                "has_fallback_chains": bool(self.global_config.get("fallback_chains")),
                "content_routing_enabled": bool(self.global_config.get("content_routing")),
                "performance_tuning_enabled": bool(self.global_config.get("performance_tuning")),
                "configuration_files": {
                    "registry_exists": self.registry_file.exists(),
                    "runtime_state_exists": self.runtime_state_file.exists()
                }
            }
            
            return summary
            
        except Exception as e:
            log_error(f"Failed to get configuration summary: {e}")
            return {}
