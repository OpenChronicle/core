# OpenChronicle Configuration Utilities

This directory contains utility scripts for managing your OpenChronicle configuration.

## Utilities

### `validate_models.py`
Validates your `models.json` configuration and checks for common issues.

**Usage:**
```bash
python utilities/validate_models.py
```

**Features:**
- ✅ Validates configuration structure
- 🔍 Checks for missing API keys
- 📊 Provides summary of configured adapters
- 💡 Gives recommendations for model upgrades

### `update_models.py`
Interactive helper for safely updating your `models.json` configuration.

**Usage:**
```bash
python utilities/update_models.py
```

**Features:**
- 💾 Automatic backup before changes
- ➕ Add new adapters
- 📝 Update model lists
- 🔧 Interactive configuration

## Best Practices

### 1. **Always Backup**
Both utilities automatically create backups, but you can also manually backup:
```bash
cp config/models.json config/models.json.backup
```

### 2. **Validate After Changes**
Always run validation after updating:
```bash
python utilities/validate_models.py
```

### 3. **Test After Updates**
Test your configuration after changes:
```bash
python main.py --test
```

### 4. **Version Control**
- ✅ Commit `models.json` changes to version control
- ❌ Don't commit files with actual API keys
- 💡 Use environment variables for sensitive data

## Environment Variables

Set these environment variables instead of hardcoding API keys:

```bash
# OpenAI
export OPENAI_API_KEY="your-key-here"

# Anthropic
export ANTHROPIC_API_KEY="your-key-here"

# Google Gemini
export GOOGLE_API_KEY="your-key-here"

# Groq
export GROQ_API_KEY="your-key-here"

# Cohere
export COHERE_API_KEY="your-key-here"

# Mistral
export MISTRAL_API_KEY="your-key-here"

# HuggingFace
export HUGGINGFACE_API_KEY="your-key-here"

# Stability AI
export STABILITY_API_KEY="your-key-here"

# Replicate
export REPLICATE_API_TOKEN="your-key-here"
```

## Configuration Updates

When providers release new models or update APIs:

1. **Check Provider Documentation**: Review the provider's API docs for changes
2. **Test New Models**: Use the update script to add new models
3. **Validate**: Run the validation script
4. **Test**: Run your application tests
5. **Deploy**: Update your production configuration

This approach gives you **controlled updates** without the risks of dynamic configuration.
