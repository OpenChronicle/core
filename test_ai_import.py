#!/usr/bin/env python3
"""
Test script for AI-powered storypack import functionality.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utilities.storypack_importer import StorypackImporter
from utilities.logging_system import get_logger


async def test_ai_import():
    """Test the AI import functionality."""
    print(">>> OpenChronicle AI Import Test")
    print("=" * 40)
    
    start_time = time.time()
    logger = get_logger()
    ai_ready = False
    
    try:
        # Initialize the importer
        print(">>> Initializing import engine...")
        importer = StorypackImporter()
        
        # Initialize AI
        print("\n>>> Initializing AI capabilities...")
        ai_initialized = importer.initialize_ai()
        
        if not ai_initialized:
            print(">>> WARNING: AI initialization failed - testing will be limited")
            print("    This could mean:")
            print("    - No model configuration found")
            print("    - ModelManager initialization failed")
            print("    - ContentAnalyzer not available")
        else:
            print(">>> AI initialized successfully")
            
            print(f">>> AI Testing Started - Model Discovery & Validation")
            
            # Test AI capabilities
            ai_ready = await importer.test_ai_capabilities()
            
            if ai_ready:
                print(f">>> SUCCESS: AI models are ready for enhanced import processing!")
            else:
                print(f">>> INFO: Import will proceed with basic functionality only")
                
    except Exception as e:
        print(f">>> ERROR: AI testing failed: {e}")
    
    print(f"\n>>> AI Import Test Complete!")
    print(f"    Duration: {time.time() - start_time:.2f} seconds")
    print(f"    Status: {'READY' if ai_ready else 'LIMITED'}")
    print(f"    Next: Run full import test with: python main.py --test")


if __name__ == "__main__":
    asyncio.run(test_ai_import())
