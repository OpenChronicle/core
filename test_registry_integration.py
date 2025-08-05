#!/usr/bin/env python3
"""
Quick integration test for registry schema validation
"""

import tempfile
import json
from pathlib import Path
import sys
import os

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.model_registry.registry_manager import RegistryManager

def test_registry_integration():
    """Test the enhanced registry manager with schema validation."""
    
    # Create a temporary directory for test configs
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test registry config
        test_registry = {
            "models": {
                "gpt-4": {
                    "name": "gpt-4",
                    "provider": "openai",
                    "priority": 1,
                    "enabled": True,
                    "capabilities": ["text_generation", "conversation"],
                    "fallbacks": ["gpt-3.5-turbo"]
                },
                "gpt-3.5-turbo": {
                    "name": "gpt-3.5-turbo", 
                    "provider": "openai",
                    "priority": 2,
                    "enabled": True,
                    "capabilities": ["text_generation", "conversation"],
                    "fallbacks": []
                }
            },
            "providers": {
                "openai": {
                    "type": "openai",
                    "api_key_env": "OPENAI_API_KEY",
                    "enabled": True
                }
            },
            "content_routing": {
                "text_generation": {
                    "primary": "gpt-4",
                    "fallbacks": ["gpt-3.5-turbo"]
                }
            },
            "performance": {
                "concurrent_requests": 10,
                "timeout_seconds": 30,
                "retry_attempts": 3
            },
            "fallback_behavior": {
                "auto_fallback": True,
                "fallback_delay": 1.0,
                "max_fallback_depth": 3
            }
        }
        
        # Create config directory structure
        config_dir = temp_path / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Save test config
        registry_file = config_dir / "test_registry.json"
        with open(registry_file, 'w') as f:
            json.dump(test_registry, f, indent=2)
        
        # Test registry manager with schema validation
        print("Testing Registry Manager with Schema Validation...")
        
        # Initialize registry manager
        manager = RegistryManager(str(config_dir))
        
        # Test registry validation
        print("✓ Registry loaded successfully")
        
        # Test validate_registry method
        try:
            manager.validate_registry()
            print("✓ Registry validation passed")
        except Exception as e:
            print(f"✗ Registry validation failed: {e}")
            return False
        
        # Test invalid config detection
        # Create invalid registry
        invalid_registry = {
            "models": {
                "invalid_model": {
                    "name": "invalid_model",
                    "provider": "nonexistent",  # Invalid provider
                    "priority": "invalid",  # Should be int
                    "enabled": True
                }
            },
            "providers": {},
            "content_routing": {},
            "performance": {},
            "fallback_behavior": {}
        }
        
        invalid_file = config_dir / "invalid_registry.json"
        with open(invalid_file, 'w') as f:
            json.dump(invalid_registry, f, indent=2)
        
        try:
            from core.model_registry.schema_validation import RegistryValidator
            validator = RegistryValidator()
            validator.validate_registry_file(str(invalid_file))
            print("✗ Should have failed validation for invalid config")
            return False
        except Exception:
            print("✓ Invalid config correctly rejected")
        
        # Test the convenience function for direct model config validation  
        from core.model_registry.schema_validation import ModelConfig
        
        valid_model_config = {
            "name": "test_model",
            "priority": 3,
            "fallbacks": [],
            "enabled": True,
            "content_types": ["safe"]
        }
        
        try:
            ModelConfig(**valid_model_config)
            print("✓ Valid model config correctly accepted")
        except Exception as e:
            print(f"✗ Valid model config rejected: {e}")
            return False
        
        print("\n🎉 All registry integration tests passed!")
        return True

if __name__ == "__main__":
    success = test_registry_integration()
    sys.exit(0 if success else 1)
