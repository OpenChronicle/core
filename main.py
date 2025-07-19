import asyncio
import sys
from pathlib import Path
from core.story_loader import load_storypack
from core.context_builder import build_context_with_analysis
from core.memory_manager import (
    load_current_memory, 
    update_character_memory, 
    add_recent_event,
    add_memory_flag,
    get_memory_summary
)
from core.scene_logger import save_scene
from core.rollback_engine import get_rollback_candidates, rollback_to_scene
from core.model_adapter import model_manager
from core.content_analyzer import ContentAnalyzer
from core.image_generation_engine import create_image_engine, ImageType

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent / "utilities"))
from logging_system import log_model_interaction, log_system_event, log_info, log_error

def print_memory_summary(story_id):
    """Print a summary of current memory state."""
    summary = get_memory_summary(story_id)
    print(f"\n📊 Memory Summary:")
    print(f"   Characters: {summary['character_count']}")
    print(f"   World State: {len(summary['world_state_keys'])} keys")
    print(f"   Active Flags: {len(summary['active_flags'])}")
    print(f"   Recent Events: {summary['recent_events_count']}")
    print(f"   Last Updated: {summary['last_updated']}")

def show_model_info():
    """Show information about available models."""
    print("\n🤖 Available Models:")
    for adapter_name in model_manager.get_available_adapters():
        try:
            info = model_manager.get_adapter_info(adapter_name)
            status = "✅ Ready" if info["initialized"] else "⏳ Not initialized"
            print(f"   {adapter_name}: {info['provider']} - {info['model_name']} ({status})")
        except Exception as e:
            print(f"   {adapter_name}: ❌ Error: {e}")
            log_error(f"Model adapter error for {adapter_name}: {e}")

async def switch_model():
    """Switch the active model adapter."""
    adapters = model_manager.get_available_adapters()
    print("\n🔄 Available Adapters:")
    for i, adapter in enumerate(adapters):
        print(f"{i+1}. {adapter}")
    
    choice = input("Select adapter number (or press Enter to cancel): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(adapters):
        adapter_name = adapters[int(choice)-1]
        try:
            print(f"🔄 Initializing {adapter_name}...")
            success = await model_manager.initialize_adapter(adapter_name)
            if success:
                model_manager.default_adapter = adapter_name
                print(f"✅ Switched to {adapter_name}")
            else:
                print(f"❌ Failed to initialize {adapter_name}")
                log_error(f"Failed to initialize adapter: {adapter_name}")
        except Exception as e:
            print(f"❌ Error switching to {adapter_name}: {e}")
            log_error(f"Error switching to adapter {adapter_name}: {e}")

def show_rollback_options(story_id):
    """Show available rollback options."""
    candidates = get_rollback_candidates(story_id, limit=5)
    if not candidates:
        print("No rollback candidates available.")
        return
    
    choice = input("Enter number to rollback (or press Enter to skip): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(candidates):
        scene_id = candidates[int(choice)-1]['scene_id']
        result = rollback_to_scene(story_id, scene_id)
        print(f"✅ {result['message']}")
        print(f"   Scenes removed: {result['scenes_removed']}")

async def show_image_commands(story_id):
    """Show and handle image generation commands."""
    print("\n🎨 Image Generation Commands:")
    print("1. Generate character portrait")
    print("2. Generate scene image")
    print("3. List existing images")
    print("4. View image stats")
    print("5. Back to main menu")
    
    choice = input("Select option (1-5): ").strip()
    
    try:
        image_engine = create_image_engine(story_id)
        
        if choice == "1":
            await generate_character_portrait_cli(image_engine)
        elif choice == "2":
            await generate_scene_image_cli(image_engine)
        elif choice == "3":
            list_existing_images(image_engine)
        elif choice == "4":
            show_image_stats(image_engine)
        elif choice == "5":
            return
        else:
            print("Invalid choice. Please select 1-5.")
    except Exception as e:
        print(f"❌ Error accessing image engine: {e}")
        log_error(f"Image engine error: {e}")

async def generate_character_portrait_cli(image_engine):
    """Generate a character portrait via CLI."""
    character_name = input("Character name: ").strip()
    if not character_name:
        print("Character name required.")
        return
    
    print("Character description (or press Enter to use default):")
    description = input().strip()
    
    character_data = {}
    if description:
        character_data["description"] = description
    else:
        character_data = {
            "description": f"A character from the story named {character_name}",
            "appearance": {"general": "Detailed character design"},
            "personality": {"demeanor": "Story-appropriate personality"}
        }
    
    print(f"🎨 Generating portrait for {character_name}...")
    
    try:
        image_id = await image_engine.generate_character_portrait(character_name, character_data)
        if image_id:
            print(f"✅ Generated portrait: {image_id}")
            image_path = image_engine.get_image_path(image_id)
            print(f"   Saved to: {image_path}")
        else:
            print("❌ Failed to generate portrait (no adapters available)")
    except Exception as e:
        print(f"❌ Error generating portrait: {e}")
        log_error(f"Portrait generation error: {e}")

async def generate_scene_image_cli(image_engine):
    """Generate a scene image via CLI."""
    scene_id = input("Scene ID (optional): ").strip()
    if not scene_id:
        scene_id = f"manual_scene_{int(asyncio.get_event_loop().time())}"
    
    description = input("Scene description: ").strip()
    if not description:
        print("Scene description required.")
        return
    
    location = input("Location (optional): ").strip()
    atmosphere = input("Atmosphere/mood (optional): ").strip()
    
    scene_data = {"description": description}
    if location:
        scene_data["location"] = location
    if atmosphere:
        scene_data["atmosphere"] = atmosphere
    
    context = {
        "manual_generation": True,
        "user_requested": True
    }
    
    print(f"🎨 Generating scene image for {scene_id}...")
    
    try:
        image_id = await image_engine.generate_scene_image(scene_id, scene_data, context)
        if image_id:
            print(f"✅ Generated scene: {image_id}")
            image_path = image_engine.get_image_path(image_id)
            print(f"   Saved to: {image_path}")
        else:
            print("❌ Failed to generate scene (no adapters available)")
    except Exception as e:
        print(f"❌ Error generating scene: {e}")
        log_error(f"Scene generation error: {e}")

def list_existing_images(image_engine):
    """List all existing images."""
    if not image_engine.metadata:
        print("No images found.")
        return
    
    print(f"\n🖼️ Existing Images ({len(image_engine.metadata)}):")
    
    characters = {}
    scenes = {}
    
    for image_id, metadata in image_engine.metadata.items():
        if metadata.image_type == ImageType.CHARACTER:
            char_name = metadata.character_name or "Unknown"
            if char_name not in characters:
                characters[char_name] = []
            characters[char_name].append(metadata)
        elif metadata.image_type == ImageType.SCENE:
            scene_id = metadata.scene_id or "Unknown"
            if scene_id not in scenes:
                scenes[scene_id] = []
            scenes[scene_id].append(metadata)
    
    if characters:
        print("\n👥 Character Portraits:")
        for char_name, images in characters.items():
            print(f"   {char_name}: {len(images)} image(s)")
            for img in images:
                print(f"     - {img.image_id} ({img.timestamp})")
    
    if scenes:
        print("\n🎬 Scene Images:")
        for scene_id, images in scenes.items():
            print(f"   {scene_id}: {len(images)} image(s)")
            for img in images:
                print(f"     - {img.image_id} ({img.timestamp})")

def show_image_stats(image_engine):
    """Show image generation statistics."""
    stats = image_engine.get_engine_stats()
    
    print(f"\n📊 Image Generation Stats:")
    print(f"   Images Generated: {stats['images_generated']}")
    print(f"   Total Cost: ${stats['total_cost']:.4f}")
    print(f"   Generation Time: {stats['generation_time']:.2f}s")
    print(f"   Available Adapters: {', '.join(stats['available_adapters'])}")
    
    if stats['providers_used']:
        print(f"   Providers Used: {', '.join(stats['providers_used'])}")
    
    total_images = stats.get('total_images', 0)
    if total_images > 0:
        print(f"   Average Cost per Image: ${stats['total_cost']/total_images:.4f}")
        print(f"   Average Time per Image: {stats['generation_time']/total_images:.2f}s")

async def run_quick_test():
    """Run a quick test of core functionality without interactive mode."""
    print("🧪 Quick Test Mode - Non-Interactive")
    print("=" * 40)
    
    try:
        # Load story
        print("📚 Loading demo story...")
        story = load_storypack("demo-story")
        story_id = story["id"]
        print(f"✅ Loaded: {story['meta']['title']}")
        
        # Initialize model
        print("🤖 Initializing mock model...")
        await model_manager.initialize_adapter("mock")
        print("✅ Mock model ready")
        
        # Test context building
        print("🏗️ Testing context building...")
        context = await build_context_with_analysis("I look around the room", story)
        print("✅ Context built successfully")
        
        # Test AI response
        print("🤖 Testing AI response...")
        response = await model_manager.generate_response(context["full_context"])
        print(f"✅ Response: {response[:50]}...")
        
        # Test scene logging
        print("📝 Testing scene logging...")
        scene_id = save_scene(story_id, "Test input", response, memory_snapshot=context["memory"])
        print(f"✅ Scene logged: {scene_id}")
        
        # Test memory summary
        print("🧠 Testing memory summary...")
        summary = get_memory_summary(story_id)
        print(f"✅ Memory summary: {summary['character_count']} characters")
        
        print("\n🎉 Quick test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await model_manager.shutdown()

async def main():
    # Check for non-interactive test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        success = await run_quick_test()
        sys.exit(0 if success else 1)
    
    print("🔧 Loading storypack...")
    story = load_storypack("demo-story")
    story_id = story["id"]
    
    print(f"✅ Loaded story: {story['meta']['title']}")
    print_memory_summary(story_id)
    
    # Initialize default model adapter
    print("🤖 Initializing AI model...")
    try:
        await model_manager.initialize_adapter(model_manager.config["default_adapter"])
        print(f"✅ Model ready: {model_manager.default_adapter}")
    except Exception as e:
        print(f"⚠️ Model initialization failed: {e}")
        print("Continuing with mock responses...")
    
    print("\n📖 Commands:")
    print("   - Type your story input normally")
    print("   - Type 'memory' to view memory summary")
    print("   - Type 'rollback' to see rollback options")
    print("   - Type 'models' to see available models")
    print("   - Type 'switch' to switch model")
    print("   - Type 'images' to access image generation")
    print("   - Type 'quit' to exit")
    
    while True:
        user_input = input("\n🧠 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        elif user_input.lower() == 'memory':
            print_memory_summary(story_id)
            continue
        elif user_input.lower() == 'rollback':
            show_rollback_options(story_id)
            continue
        elif user_input.lower() == 'models':
            show_model_info()
            continue
        elif user_input.lower() == 'switch':
            await switch_model()
            continue
        elif user_input.lower() == 'images':
            await show_image_commands(story_id)
            continue
        elif not user_input:
            continue
        
        # Build context using intelligent analysis
        context = await build_context_with_analysis(user_input, story)
        
        # Get routing recommendation from analysis
        routing = context.get("routing", {})
        preferred_adapter = routing.get("adapter", model_manager.default_adapter)
        max_tokens = routing.get("max_tokens", 1024)
        temperature = routing.get("temperature", 0.7)
        
        # Generate AI response using optimized context and routing
        try:
            ai_response = await model_manager.generate_response(
                context["full_context"], 
                adapter_name=preferred_adapter,
                story_id=story_id,
                max_tokens=max_tokens,
                temperature=temperature
            )
        except Exception as e:
            print(f"⚠️ AI generation failed: {e}")
            ai_response = f"[Error generating response: {e}]"
        
        # Generate content flags from analysis and response
        analysis = context.get("analysis", {})
        if analysis:
            try:
                content_analyzer_instance = ContentAnalyzer(model_manager)
                content_flags = await content_analyzer_instance.generate_content_flags(analysis, ai_response)
                for flag in content_flags:
                    add_memory_flag(story_id, flag["name"], flag["value"])
                print(f"   Generated {len(content_flags)} content flags")
            except Exception as e:
                print(f"⚠️ Flag generation failed: {e}")
        
        # Log the scene
        scene_id = save_scene(
            story_id, 
            user_input, 
            ai_response, 
            memory_snapshot=context["memory"],
            analysis_data=analysis
        )
        
        # Add to recent events
        add_recent_event(story_id, f"User: {user_input}")
        
        print(f"📖 {ai_response}")
        print(f"   Scene logged: {scene_id}")
    
    print("\n👋 Story session ended.")
    await model_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())