# 🧙 OpenChronicle
## 🔧 Core Features (v0.1.x)

- 🧱 **Modular scene prompt builder** with canon/context injection
- 🧠 **Advanced memory management** with character tracking, world state, and flags
- 🔄 **Scene rollback system** with automatic backups and integrity validation
- 🤖 **Multi-model LLM support** with unified adapter system (OpenAI, Ollama, mock)
- � **Intelligent content analysis** with local LLM preprocessing for token optimization
- �📄 **Canon-aware context building** with structured memory integration
- 🗂️ **Story project folders** with structured metadata and modular storypacks
- 📝 **Comprehensive scene logging** with memory snapshots and rollback points
- 🎯 **Lightweight and portable** - optimized for Docker, Raspberry Pi, and cloud deployment

---

## 🧠 Content Analysis System

OpenChronicle uses a local LLM to analyze and optimize content before sending to the main model:

### Features
- **Content Classification**: Analyzes user input for type, intent, and entities
- **Token Optimization**: Reduces context size by 50-80% through smart selection
- **Automatic Flagging**: Generates memory flags from content analysis
- **Smart Routing**: Routes content to appropriate models based on analysis
- **NSFW Detection**: Content filtering and model routing for sensitive content

### Two-Tier Architecture
1. **Local LLM** (fast, cheap): Content analysis, classification, context filtering
2. **Main LLM** (OpenAI/Ollama): Story generation with optimized prompts

### Benefits
- **Reduced Token Costs**: Smart context selection minimizes API usage
- **Faster Responses**: Smaller, optimized prompts improve response times
- **Better Content Handling**: Automatic classification and routing
- **Enhanced Memory**: Automatic flag generation and entity extraction

---

## 🤖 Model Adapter System

OpenChronicle supports multiple LLM backends through a unified adapter system:

### Supported Models
- **OpenAI**: GPT-4, GPT-4o-mini, GPT-3.5-turbo
- **Ollama**: Any locally hosted model (Llama, Mistral, etc.)
- **Mock**: Built-in testing adapter

### Configuration
Models are configured in `config/models.json`:

```json
{
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
      "base_url": "http://localhost:11434"
    }
  }
}
```

### CLI Commands
- `models` - Show available model adapters
- `switch` - Switch between model adapters
- `memory` - View current memory state
- `rollback` - Access rollback options

---nicle** is a modular, AI-powered interactive storytelling engine built to support dynamic worldbuilding, persistent memory, character-driven narratives, and multi-model orchestration — all within a portable, Docker-ready framework.

Craft immersive, branching story worlds using GPT-4o, Claude, or local LLMs — with full control over continuity, tone, and content.

> "Build once. Run anywhere. Remember everything."

---

## ✨ Project Goals

- 🧠 Enable **seamless narrative continuity** across sessions and branches
- ⚙️ Support **model-agnostic orchestration** (OpenAI, Anthropic, local LLMs)
- 📚 Manage **canonical memory**, player flags, and emotional arcs automatically
- 🔍 Integrate **content classification and routing logic** (e.g., NSFW handling)
- 🐳 Deploy anywhere with a **lightweight Docker container**
- 🧩 Allow creators to plug in their own **stories, worlds, and character packs**

---

## 🔧 Core Features (v0.1.x)

- 🧱 **Modular scene prompt builder** with canon/context injection
- 🧠 **Advanced memory management** with character tracking, world state, and flags
- 🔄 **Scene rollback system** with automatic backups and integrity validation
- � **Canon-aware context building** with structured memory integration
- 🗂️ **Story project folders** with structured metadata and modular storypacks
- � **Comprehensive scene logging** with memory snapshots and rollback points
- 🎯 **Lightweight and portable** - optimized for Docker, Raspberry Pi, and cloud deployment

---

## 📦 Getting Started

### 🐳 Docker Quick Start (Recommended)

OpenChronicle includes embedded Ollama with Llama 3.2 models for complete self-containment:

```bash
# Clone the repository
git clone https://github.com/OpenChronicle/openchronicle-core.git
cd openchronicle-core

# Start the complete environment (downloads ~2GB of models on first run)
docker-compose up -d

# Start interactive storytelling
docker-compose exec openchronicle python main.py

# Check status
docker-compose logs -f openchronicle
docker-compose logs -f ollama

# Stop services
docker-compose down
```

### 🛠️ Local Development

For development or external LLM integration:

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
# or
source .venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run with local Ollama (install separately)
python main.py
```

### ☁️ Cloud Deployment

For cloud deployment with OpenAI:

```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key"

# Update config/models.json to use OpenAI adapter
# Run the application
python main.py
```

### 🔧 Configuration

Models are configured in `config/models.json`. The Docker setup uses embedded Ollama by default, but you can modify the configuration for different deployment scenarios.

---

## 🐳 Docker Architecture

OpenChronicle uses a multi-container architecture for complete self-containment:

```yaml
services:
  openchronicle:    # Main application
    - Python 3.11 with OpenChronicle
    - SQLite databases
    - Story management
    
  ollama:           # Embedded LLM service
    - Llama 3.2 1B (content analysis)
    - Llama 3.2 3B (story generation)
    - Completely local, no external APIs
```

### Benefits
- **Complete Self-Containment**: No external dependencies
- **Privacy**: All processing happens locally
- **Cost-Effective**: No API fees
- **Portable**: Runs anywhere Docker runs
- **Scalable**: Easy to swap models or add GPUs

---
This project is dual-licensed under AGPL-3.0 for engine code and CC BY-NC-SA 4.0 for story content.

![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)
![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/Content%20License-CC%20BY--NC--SA%204.0-lightgrey.svg)
