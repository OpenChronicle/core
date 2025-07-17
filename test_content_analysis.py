"""
Test the content analysis system.
"""

import asyncio
import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.content_analyzer import content_analyzer
from core.model_adapter import model_manager
from core.story_loader import load_storypack
from core.context_builder import build_context_with_analysis

async def test_content_analysis():
    """Test the content analysis system."""
    print("🧪 Testing Content Analysis System")
    print("=" * 50)
    
    # Initialize model manager
    await model_manager.initialize_adapter("mock")
    
    # Load demo story
    story = load_storypack("demo-story")
    
    # Test inputs
    test_inputs = [
        "I draw my sword and challenge the dragon to battle!",
        "Hello, my name is Sarah. What's your name?",
        "I look around the mysterious forest, trying to understand where I am.",
        "Can you tell me more about this place?",
        "I cast a fireball spell at the approaching enemies."
    ]
    
    print("\n1. Testing Content Analysis:")
    for i, user_input in enumerate(test_inputs):
        print(f"\n   Test {i+1}: {user_input}")
        
        try:
            # Test analysis
            story_context = {
                "story_id": story["id"],
                "meta": story.get("meta", {}),
                "characters": {}
            }
            
            analysis = await content_analyzer.analyze_user_input(user_input, story_context)
            print(f"   Content Type: {analysis.get('content_type', 'unknown')}")
            print(f"   Intent: {analysis.get('intent', 'unknown')}")
            print(f"   Entities: {analysis.get('entities', {})}")
            print(f"   Flags: {analysis.get('content_flags', {})}")
            
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n2. Testing Context Building with Analysis:")
    test_input = "I approach the ancient castle and knock on the door."
    
    try:
        context = await build_context_with_analysis(test_input, story)
        print(f"   Context length: {len(context['full_context'])} characters")
        print(f"   Canon used: {len(context['canon_used'])} snippets")
        print(f"   Analysis present: {context['analysis'] is not None}")
        
        if context['analysis']:
            print(f"   Content type: {context['analysis'].get('content_type', 'unknown')}")
            print(f"   Token priority: {context['analysis'].get('token_priority', 'unknown')}")
        
        if context.get('routing'):
            routing = context['routing']
            print(f"   Recommended adapter: {routing.get('adapter', 'unknown')}")
            print(f"   Max tokens: {routing.get('max_tokens', 'unknown')}")
            print(f"   Temperature: {routing.get('temperature', 'unknown')}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n3. Testing Content Flag Generation:")
    try:
        # Mock analysis and response
        mock_analysis = {
            "content_type": "action",
            "entities": {
                "characters": ["hero"],
                "locations": ["castle"],
                "items": ["sword"]
            },
            "content_flags": {
                "nsfw": False,
                "violence": True,
                "emotional_intensity": "high"
            }
        }
        
        mock_response = "The hero draws their sword and approaches the castle gate."
        
        flags = await content_analyzer.generate_content_flags(mock_analysis, mock_response)
        print(f"   Generated {len(flags)} flags:")
        for flag in flags:
            print(f"     - {flag['name']}: {flag['value']}")
    
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n4. Testing Routing Recommendations:")
    try:
        # Test different content types
        test_analyses = [
            {"content_flags": {"nsfw": True}, "token_priority": "high"},
            {"content_flags": {"violence": True}, "token_priority": "medium"},
            {"content_type": "dialogue", "token_priority": "low"}
        ]
        
        for i, analysis in enumerate(test_analyses):
            routing = content_analyzer.get_routing_recommendation(analysis)
            print(f"   Test {i+1}: {routing}")
    
    except Exception as e:
        print(f"   Error: {e}")
    
    # Shutdown
    await model_manager.shutdown()
    print("\n🎉 Content analysis tests completed!")

if __name__ == "__main__":
    asyncio.run(test_content_analysis())
