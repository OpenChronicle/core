from core.story_loader import load_storypack
from core.context_builder import build_context

if __name__ == "__main__":
    print("🔧 Loading storypack...")
    story = load_storypack("demo-story")
    
    print(f"✅ Loaded story: {story['meta']['title']}")
    while True:
        user_input = input("🧠 You: ")
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        context = build_context(user_input, story)
        print(f"📖 Context built successfully. Prompt length: {len(context['prompt'])} chars")