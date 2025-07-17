#!/usr/bin/env python3
"""
Model configuration validation script.
Run this periodically to check your models.json configuration.
"""

import json
import os
import sys
import asyncio
from pathlib import Path

# Add the parent directory to the path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.model_adapter import ModelManager

async def validate_models():
    """Validate all configured models and check their availability."""
    
    print("🔍 Validating models.json configuration...")
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "models.json"
    if not config_path.exists():
        print("❌ models.json not found!")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    manager = ModelManager()
    results = {}
    
    # Test each adapter
    for adapter_name, adapter_config in config["adapters"].items():
        # Skip comments and mock adapters
        if adapter_name.startswith("//") or adapter_config.get("type") in ["mock", "mock_image"]:
            continue
            
        print(f"\n📡 Testing {adapter_name}...")
        
        try:
            # Try to initialize the adapter
            if adapter_config.get("type") in ["openai_image", "stability", "replicate"]:
                # Image generation test
                if adapter_config.get("api_key") or os.getenv(f"{adapter_config['type'].upper()}_API_KEY"):
                    print(f"  ✅ {adapter_name}: Configuration valid (API key found)")
                    results[adapter_name] = "configured"
                else:
                    print(f"  ⚠️  {adapter_name}: Missing API key")
                    results[adapter_name] = "missing_key"
            else:
                # Text generation test
                if adapter_config.get("type") == "ollama":
                    print(f"  ✅ {adapter_name}: Ollama endpoint configured")
                    results[adapter_name] = "configured"
                elif adapter_config.get("api_key") or os.getenv(f"{adapter_config['type'].upper()}_API_KEY"):
                    print(f"  ✅ {adapter_name}: Configuration valid (API key found)")
                    results[adapter_name] = "configured"
                else:
                    print(f"  ⚠️  {adapter_name}: Missing API key")
                    results[adapter_name] = "missing_key"
                    
        except Exception as e:
            print(f"  ❌ {adapter_name}: Error - {str(e)}")
            results[adapter_name] = "error"
    
    # Summary
    print("\n📊 Validation Summary:")
    configured = sum(1 for status in results.values() if status == "configured")
    missing_keys = sum(1 for status in results.values() if status == "missing_key")
    errors = sum(1 for status in results.values() if status == "error")
    
    print(f"  ✅ Configured: {configured}")
    print(f"  ⚠️  Missing keys: {missing_keys}")
    print(f"  ❌ Errors: {errors}")
    
    if missing_keys > 0:
        print("\n💡 To fix missing keys, either:")
        print("  1. Set environment variables (e.g., OPENAI_API_KEY)")
        print("  2. Add api_key values to models.json (not recommended for production)")
    
    return errors == 0

async def check_model_availability():
    """Check if configured models are still available from providers."""
    print("\n🔍 Checking model availability...")
    
    # This could be expanded to actually query provider APIs
    # For now, just check the configuration structure
    config_path = Path(__file__).parent.parent / "config" / "models.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    recommendations = []
    
    for adapter_name, adapter_config in config["adapters"].items():
        if adapter_name.startswith("//") or adapter_config.get("type") in ["mock", "mock_image"]:
            continue
            
        # Check for outdated model names (examples)
        model_name = adapter_config.get("model_name", "")
        
        if "gpt-3.5-turbo" in model_name:
            recommendations.append(f"Consider upgrading {adapter_name} to gpt-4o-mini for better performance")
        elif "claude-3-haiku" in model_name:
            recommendations.append(f"Consider upgrading {adapter_name} to claude-3-5-sonnet for better performance")
    
    if recommendations:
        print("\n💡 Model Recommendations:")
        for rec in recommendations:
            print(f"  • {rec}")
    else:
        print("  ✅ All models appear to be current")

if __name__ == "__main__":
    asyncio.run(validate_models())
    asyncio.run(check_model_availability())
