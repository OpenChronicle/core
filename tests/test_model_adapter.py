"""
Test suite for Model Adapter

Tests model management, API integration, and adaptive model selection.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from core.model_adapter import (
    ModelManager,
    ModelAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    MockAdapter
)


@pytest.fixture
def sample_config():
    """Sample model configuration."""
    return {
        "model_name": "test-model",
        "api_endpoint": "https://api.test.com/v1",
        "api_key": "test-key-123",
        "max_tokens": 2048,
        "temperature": 0.7
    }


@pytest.fixture
def mock_openai_adapter():
    """Mock OpenAI adapter."""
    adapter = Mock()
    adapter.name = "openai"
    adapter.supports_streaming = True
    adapter.max_tokens = 4096
    adapter.generate = AsyncMock(return_value="Mock OpenAI response")
    adapter.get_info = Mock(return_value={
        "name": "openai",
        "model": "gpt-4",
        "max_tokens": 4096,
        "supports_streaming": True
    })
    return adapter


@pytest.fixture 
def mock_anthropic_adapter():
    """Mock Anthropic adapter."""
    adapter = Mock()
    adapter.name = "anthropic"
    adapter.supports_streaming = True
    adapter.max_tokens = 8192
    adapter.generate = AsyncMock(return_value="Mock Anthropic response")
    adapter.get_info = Mock(return_value={
        "name": "anthropic", 
        "model": "claude-3",
        "max_tokens": 8192,
        "supports_streaming": True
    })
    return adapter


class TestAdapterRegistry:
    """Test adapter registry functionality."""
    
    def test_register_adapter(self, mock_openai_adapter):
        """Test registering an adapter."""
        registry = AdapterRegistry()
        
        registry.register("openai", mock_openai_adapter)
        
        assert "openai" in registry.adapters
        assert registry.adapters["openai"] == mock_openai_adapter
    
    def test_get_adapter_success(self, mock_openai_adapter):
        """Test getting a registered adapter."""
        registry = AdapterRegistry()
        registry.register("openai", mock_openai_adapter)
        
        adapter = registry.get_adapter("openai")
        
        assert adapter == mock_openai_adapter
    
    def test_get_adapter_not_found(self):
        """Test getting non-existent adapter."""
        registry = AdapterRegistry()
        
        with pytest.raises(ValueError, match="Adapter 'nonexistent' not found"):
            registry.get_adapter("nonexistent")
    
    def test_list_adapters(self, mock_openai_adapter, mock_anthropic_adapter):
        """Test listing available adapters."""
        registry = AdapterRegistry()
        registry.register("openai", mock_openai_adapter)
        registry.register("anthropic", mock_anthropic_adapter)
        
        adapters = registry.list_adapters()
        
        assert set(adapters) == {"openai", "anthropic"}
    
    def test_is_available(self, mock_openai_adapter):
        """Test checking adapter availability."""
        registry = AdapterRegistry()
        registry.register("openai", mock_openai_adapter)
        
        assert registry.is_available("openai")
        assert not registry.is_available("nonexistent")


class TestModelManager:
    """Test ModelManager functionality."""
    
    def test_init_with_config(self, sample_config):
        """Test ModelManager initialization with config."""
        manager = ModelManager(sample_config)
        
        assert manager.config == sample_config
        assert manager.current_adapter is None
    
    def test_init_without_config(self):
        """Test ModelManager initialization without config."""
        manager = ModelManager()
        
        assert manager.config == {}
        assert manager.current_adapter is None
    
    @pytest.mark.asyncio
    async def test_set_adapter_success(self, mock_openai_adapter, sample_config):
        """Test setting adapter successfully."""
        manager = ModelManager(sample_config)
        
        with patch.object(manager.registry, 'get_adapter', return_value=mock_openai_adapter):
            await manager.set_adapter("openai")
        
        assert manager.current_adapter == mock_openai_adapter
        assert manager.adapter_name == "openai"
    
    @pytest.mark.asyncio
    async def test_set_adapter_not_found(self, sample_config):
        """Test setting non-existent adapter."""
        manager = ModelManager(sample_config)
        
        with patch.object(manager.registry, 'get_adapter', side_effect=ValueError("Not found")):
            with pytest.raises(ValueError, match="Not found"):
                await manager.set_adapter("nonexistent")
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, mock_openai_adapter, sample_config):
        """Test successful response generation."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        manager.adapter_name = "openai"
        
        response = await manager.generate_response("Test prompt")
        
        assert response == "Mock OpenAI response"
        mock_openai_adapter.generate.assert_called_once_with("Test prompt", sample_config)
    
    @pytest.mark.asyncio
    async def test_generate_response_no_adapter(self, sample_config):
        """Test response generation without adapter set."""
        manager = ModelManager(sample_config)
        
        with pytest.raises(RuntimeError, match="No adapter set"):
            await manager.generate_response("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_response_with_fallback(self, mock_openai_adapter, mock_anthropic_adapter, sample_config):
        """Test response generation with fallback on failure."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        manager.adapter_name = "openai"
        
        # Make primary adapter fail
        mock_openai_adapter.generate.side_effect = Exception("API Error")
        
        # Set up fallback
        with patch.object(manager.registry, 'get_adapter', return_value=mock_anthropic_adapter):
            with patch.object(manager, '_get_fallback_adapter', return_value="anthropic"):
                response = await manager.generate_response("Test prompt", enable_fallback=True)
        
        assert response == "Mock Anthropic response"
        assert manager.current_adapter == mock_anthropic_adapter
    
    def test_get_adapter_info(self, mock_openai_adapter, sample_config):
        """Test getting adapter information."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        
        info = manager.get_adapter_info()
        
        assert info["name"] == "openai"
        assert info["max_tokens"] == 4096
    
    def test_get_adapter_info_no_adapter(self, sample_config):
        """Test getting adapter info without adapter set."""
        manager = ModelManager(sample_config)
        
        info = manager.get_adapter_info()
        
        assert info == {}
    
    def test_is_streaming_supported(self, mock_openai_adapter, sample_config):
        """Test checking streaming support."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        
        assert manager.is_streaming_supported()
    
    def test_is_streaming_supported_no_adapter(self, sample_config):
        """Test checking streaming support without adapter."""
        manager = ModelManager(sample_config)
        
        assert not manager.is_streaming_supported()
    
    def test_get_available_models(self, sample_config):
        """Test getting available models."""
        manager = ModelManager(sample_config)
        
        with patch.object(manager.registry, 'list_adapters', return_value=["openai", "anthropic"]):
            models = manager.get_available_models()
        
        assert models == ["openai", "anthropic"]
    
    def test_validate_config_valid(self):
        """Test config validation with valid config."""
        config = {
            "model_name": "test-model",
            "api_key": "test-key",
            "max_tokens": 1000
        }
        
        manager = ModelManager()
        result = manager.validate_config(config)
        
        assert result is True
    
    def test_validate_config_missing_required(self):
        """Test config validation with missing required fields."""
        config = {
            "model_name": "test-model"
            # Missing api_key
        }
        
        manager = ModelManager()
        result = manager.validate_config(config)
        
        assert result is False
    
    def test_estimate_tokens(self, sample_config):
        """Test token estimation."""
        manager = ModelManager(sample_config)
        
        # Simple estimation based on character count
        text = "This is a test prompt for token estimation."
        tokens = manager.estimate_tokens(text)
        
        assert isinstance(tokens, int)
        assert tokens > 0
    
    def test_get_fallback_adapter(self, sample_config):
        """Test fallback adapter selection."""
        manager = ModelManager(sample_config)
        manager.adapter_name = "openai"
        
        with patch.object(manager.registry, 'list_adapters', return_value=["openai", "anthropic", "ollama"]):
            fallback = manager._get_fallback_adapter()
        
        # Should return first available adapter that's not current
        assert fallback in ["anthropic", "ollama"]
        assert fallback != "openai"


class TestAdapterIntegration:
    """Test adapter integration and compatibility."""
    
    @pytest.mark.asyncio
    async def test_openai_adapter_integration(self, sample_config):
        """Test OpenAI adapter integration."""
        manager = ModelManager(sample_config)
        
        # Mock the OpenAI adapter creation
        with patch('core.model_adapter.OpenAIAdapter') as mock_adapter_class:
            mock_adapter = mock_openai_adapter()
            mock_adapter_class.return_value = mock_adapter
            
            # Register the adapter
            manager.registry.register("openai", mock_adapter)
            
            await manager.set_adapter("openai")
            response = await manager.generate_response("Test prompt")
        
        assert response == "Mock OpenAI response"
    
    @pytest.mark.asyncio
    async def test_anthropic_adapter_integration(self, sample_config):
        """Test Anthropic adapter integration."""
        manager = ModelManager(sample_config)
        
        # Mock the Anthropic adapter creation
        with patch('core.model_adapter.AnthropicAdapter') as mock_adapter_class:
            mock_adapter = mock_anthropic_adapter()
            mock_adapter_class.return_value = mock_adapter
            
            # Register the adapter
            manager.registry.register("anthropic", mock_adapter)
            
            await manager.set_adapter("anthropic")
            response = await manager.generate_response("Test prompt")
        
        assert response == "Mock Anthropic response"
    
    @pytest.mark.asyncio
    async def test_adapter_switching(self, mock_openai_adapter, mock_anthropic_adapter, sample_config):
        """Test switching between adapters."""
        manager = ModelManager(sample_config)
        
        # Register both adapters
        manager.registry.register("openai", mock_openai_adapter)
        manager.registry.register("anthropic", mock_anthropic_adapter)
        
        # Start with OpenAI
        await manager.set_adapter("openai")
        response1 = await manager.generate_response("Test prompt 1")
        assert response1 == "Mock OpenAI response"
        
        # Switch to Anthropic
        await manager.set_adapter("anthropic")
        response2 = await manager.generate_response("Test prompt 2")
        assert response2 == "Mock Anthropic response"
        
        assert manager.current_adapter == mock_anthropic_adapter


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_adapter_function(self, mock_openai_adapter):
        """Test standalone get_adapter function."""
        with patch('core.model_adapter.default_registry') as mock_registry:
            mock_registry.get_adapter.return_value = mock_openai_adapter
            
            adapter = get_adapter("openai")
        
        assert adapter == mock_openai_adapter
        mock_registry.get_adapter.assert_called_once_with("openai")
    
    def test_normalize_response_string(self):
        """Test response normalization with string input."""
        response = "This is a test response"
        
        result = normalize_response(response)
        
        assert result == response
    
    def test_normalize_response_dict(self):
        """Test response normalization with dict input."""
        response = {
            "text": "This is the response text",
            "metadata": {"tokens": 100}
        }
        
        result = normalize_response(response)
        
        assert result == "This is the response text"
    
    def test_normalize_response_dict_no_text(self):
        """Test response normalization with dict without text field."""
        response = {
            "content": "This is the content",
            "metadata": {"tokens": 100}
        }
        
        result = normalize_response(response)
        
        # Should return string representation
        assert isinstance(result, str)
        assert "content" in result
    
    def test_normalize_response_list(self):
        """Test response normalization with list input."""
        response = ["First response", "Second response"]
        
        result = normalize_response(response)
        
        assert result == "First response\nSecond response"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, mock_openai_adapter, sample_config):
        """Test handling API timeout errors."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        
        # Simulate timeout
        mock_openai_adapter.generate.side_effect = asyncio.TimeoutError("Request timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await manager.generate_response("Test prompt")
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_openai_adapter, sample_config):
        """Test handling general API errors."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        
        # Simulate API error
        mock_openai_adapter.generate.side_effect = Exception("API Error: Rate limit exceeded")
        
        with pytest.raises(Exception, match="API Error"):
            await manager.generate_response("Test prompt")
    
    @pytest.mark.asyncio
    async def test_invalid_response_handling(self, mock_openai_adapter, sample_config):
        """Test handling invalid responses."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        
        # Return invalid response type
        mock_openai_adapter.generate.return_value = None
        
        response = await manager.generate_response("Test prompt")
        
        # Should handle gracefully
        assert response is None or isinstance(response, str)


class TestPerformanceMetrics:
    """Test performance monitoring and metrics."""
    
    @pytest.mark.asyncio
    async def test_response_time_tracking(self, mock_openai_adapter, sample_config):
        """Test response time tracking."""
        manager = ModelManager(sample_config)
        manager.current_adapter = mock_openai_adapter
        
        # Add delay to simulate response time
        async def delayed_generate(prompt, config):
            await asyncio.sleep(0.1)
            return "Response with delay"
        
        mock_openai_adapter.generate = delayed_generate
        
        start_time = asyncio.get_event_loop().time()
        response = await manager.generate_response("Test prompt")
        end_time = asyncio.get_event_loop().time()
        
        assert response == "Response with delay"
        assert (end_time - start_time) >= 0.1
    
    def test_token_usage_estimation(self, sample_config):
        """Test token usage estimation."""
        manager = ModelManager(sample_config)
        
        prompt = "This is a test prompt for token estimation that is longer than usual."
        tokens = manager.estimate_tokens(prompt)
        
        assert isinstance(tokens, int)
        assert tokens > 10  # Should be reasonable estimate


if __name__ == "__main__":
    pytest.main([__file__])
