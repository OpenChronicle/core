#!/usr/bin/env python3
"""
Test script for enhanced model selection and fallback strategies
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.content_analyzer import ContentAnalyzer
from core.model_adapter import ModelManager
from utilities.logging_system import log_info, log_warning, log_error

async def test_enhanced_model_selection():
    """Test the enhanced model selection with various scenarios."""
    
    print("=" * 60)
    print("ENHANCED MODEL SELECTION TEST")
    print("=" * 60)
    
    # Initialize components
    model_manager = ModelManager()
    content_analyzer = ContentAnalyzer(model_manager)
    
    print("\n>>> Testing Model Selection Scenarios...")
    
    # Scenario 1: Analysis content with no suitable models
    print("\n1. Testing analysis content selection:")
    print("   Content type: analysis")
    analysis_model = content_analyzer.get_best_analysis_model("analysis", allow_fallbacks=True)
    print(f"   Selected model: {analysis_model}")
    
    # Scenario 2: Creative content selection  
    print("\n2. Testing creative content selection:")
    print("   Content type: creative")
    creative_model = content_analyzer.get_best_analysis_model("creative", allow_fallbacks=True)
    print(f"   Selected model: {creative_model}")
    
    # Scenario 3: NSFW content with limited options
    print("\n3. Testing NSFW content selection:")
    print("   Content type: nsfw")
    nsfw_model = content_analyzer.get_best_analysis_model("nsfw", allow_fallbacks=True)
    print(f"   Selected model: {nsfw_model}")
    
    # Scenario 4: No fallbacks allowed
    print("\n4. Testing selection with no fallbacks:")
    print("   Content type: analysis, no fallbacks")
    strict_model = content_analyzer.get_best_analysis_model("analysis", allow_fallbacks=False)
    print(f"   Selected model: {strict_model}")
    
    # Scenario 5: Test model management suggestions
    print("\n5. Testing model management suggestions:")
    suggestions = await content_analyzer.suggest_model_management_actions("analysis")
    print(f"   Suggestions available: {len(suggestions['actions'])}")
    print(f"   Priority: {suggestions['priority']}")
    for i, action in enumerate(suggestions['actions'], 1):
        print(f"   {i}. {action['type']}: {action['description']}")
        if 'commands' in action:
            for cmd in action['commands']:
                print(f"      Command: {cmd}")
        if 'models' in action:
            print(f"      Affected models: {', '.join(action['models'])}")
        if 'current_best_score' in action:
            print(f"      Current best score: {action['current_best_score']:.2f}")
    
    # Scenario 5.5: Test with simulated high resource usage
    print("\n5.5. Testing with high resource usage:")
    resource_info = {"memory_percent": 85, "cpu_percent": 90}
    resource_suggestions = await content_analyzer.suggest_model_management_actions("analysis", resource_info)
    print(f"   Resource-aware suggestions: {len(resource_suggestions['actions'])}")
    for i, action in enumerate(resource_suggestions['actions'], 1):
        if action['type'] == 'optimize_resources':
            print(f"   {i}. {action['type']}: {action['description']}")
    
    # Scenario 6: Test complete model failure scenario
    print("\n6. Testing complete model failure scenario:")
    print("   Testing with no fallbacks allowed...")
    no_fallback_model = content_analyzer.get_best_analysis_model("analysis", allow_fallbacks=False)
    print(f"   Result with no fallbacks: {no_fallback_model}")
    
    # Scenario 7: Test suitability scoring details
    print("\n7. Testing model suitability scoring:")
    test_models = ["mock", "ollama", "openai", "anthropic", "mock_image"]
    for model_name in test_models:
        suitability = content_analyzer._check_model_suitability(model_name, "analysis")
        print(f"   {model_name}: suitable={suitability['suitable']}, score={suitability['score']:.2f}")
        print(f"      Reason: {suitability['reason']}")
    
    # Scenario 8: Test different content types
    print("\n8. Testing content type variations:")
    content_types = ["creative", "nsfw", "general", "fast"]
    for ctype in content_types:
        model = content_analyzer.get_best_analysis_model(ctype, allow_fallbacks=True)
        print(f"   {ctype}: {model}")
        
    # Scenario 9: Demonstrate model guidance system
    print("\n9. Testing model guidance system:")
    print("   Simulating scenario with no suitable models...")
    # This will trigger the guidance system
    content_analyzer._provide_model_guidance("analysis", [
        ("ollama", 0.05, "Model unavailable: llama3.2:latest not found"),
        ("openai", 0.00, "API key required"),
        ("anthropic", 0.00, "API key required")
    ])
    
    print("\n>>> Model Selection Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_enhanced_model_selection())
