"""
Provider adapters package.

Individual provider implementations that inherit from BaseAPIAdapter
to eliminate code duplication.
"""

# Provider adapters - proof of concept implementations  
from .openai import OpenAIAdapter
from .ollama import OllamaAdapter
from .anthropic import AnthropicAdapter
# from .gemini import GeminiAdapter
# from .groq import GroqAdapter
# from .cohere import CohereAdapter
# from .mistral import MistralAdapter
# from .huggingface import HuggingFaceAdapter
# from .azure_openai import AzureOpenAIAdapter
# from .transformers import TransformersAdapter

__all__ = [
    # Text adapters - proof of concept
    'OpenAIAdapter',
    'OllamaAdapter',
    'AnthropicAdapter',
    
    # Additional adapters to be implemented
    # 'GeminiAdapter', 
    # 'GroqAdapter',
    # 'CohereAdapter',
    # 'MistralAdapter',
    # 'HuggingFaceAdapter',
    # 'AzureOpenAIAdapter',
    # 'TransformersAdapter',
    
    # Image adapters (to be added)
    # 'OpenAIImageAdapter',
    # 'StabilityAdapter', 
    # 'ReplicateAdapter',
]
