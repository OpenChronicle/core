"""
Test suite for Token Manager

Tests token counting, optimization, and API limit management.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from core.token_manager import (
    TokenManager,
    estimate_tokens,
    optimize_context_for_tokens,
    calculate_token_usage,
    get_model_limits,
    TokenLimitError
)


@pytest.fixture
def token_manager():
    """Create TokenManager instance for testing."""
    return TokenManager(model_name="gpt-4", max_tokens=4096)


@pytest.fixture
def sample_context():
    """Sample context for token testing."""
    return {
        "system": "You are a helpful storytelling assistant.",
        "memory": "Alice is a brave adventurer in a fantasy world. She recently helped a villager.",
        "canon": "The world is filled with magic. Characters have unique abilities.",
        "user_input": "Alice explores the mysterious forest.",
        "full_context": "Complete context with all elements combined for token estimation."
    }


class TestTokenEstimation:
    """Test token estimation functionality."""
    
    def test_estimate_tokens_simple_text(self):
        """Test token estimation for simple text."""
        text = "This is a simple test sentence."
        
        tokens = estimate_tokens(text)
        
        assert isinstance(tokens, int)
        assert tokens > 0
        assert tokens < 20  # Should be reasonable estimate
    
    def test_estimate_tokens_long_text(self):
        """Test token estimation for longer text."""
        text = "This is a much longer text that should result in more tokens. " * 50
        
        tokens = estimate_tokens(text)
        
        assert isinstance(tokens, int)
        assert tokens > 100  # Should be proportionally larger
    
    def test_estimate_tokens_empty_text(self):
        """Test token estimation for empty text."""
        tokens = estimate_tokens("")
        
        assert tokens == 0
    
    def test_estimate_tokens_special_characters(self):
        """Test token estimation with special characters."""
        text = "Hello! 🌟 How are you? #hashtag @mention https://example.com"
        
        tokens = estimate_tokens(text)
        
        assert isinstance(tokens, int)
        assert tokens > 0
    
    def test_estimate_tokens_code(self):
        """Test token estimation for code."""
        code = """
        def hello_world():
            print("Hello, world!")
            return True
        """
        
        tokens = estimate_tokens(code)
        
        assert isinstance(tokens, int)
        assert tokens > 10
    
    def test_estimate_tokens_different_models(self):
        """Test token estimation varies by model."""
        text = "This is a test sentence for token estimation."
        
        tokens_gpt4 = estimate_tokens(text, model="gpt-4")
        tokens_claude = estimate_tokens(text, model="claude-3")
        
        assert isinstance(tokens_gpt4, int)
        assert isinstance(tokens_claude, int)
        # May vary slightly between models
        assert abs(tokens_gpt4 - tokens_claude) <= 5


class TestTokenManager:
    """Test TokenManager class functionality."""
    
    def test_token_manager_init(self):
        """Test TokenManager initialization."""
        manager = TokenManager(model_name="gpt-4", max_tokens=8192)
        
        assert manager.model_name == "gpt-4"
        assert manager.max_tokens == 8192
        assert manager.reserved_tokens > 0
        assert manager.available_tokens < manager.max_tokens
    
    def test_token_manager_estimate_context(self, token_manager, sample_context):
        """Test context token estimation."""
        tokens = token_manager.estimate_context_tokens(sample_context)
        
        assert isinstance(tokens, int)
        assert tokens > 0
        assert "system_tokens" in token_manager.last_breakdown
        assert "memory_tokens" in token_manager.last_breakdown
    
    def test_token_manager_check_limits(self, token_manager):
        """Test token limit checking."""
        # Should pass with reasonable context
        short_context = {"user_input": "Short test"}
        result = token_manager.check_token_limits(short_context)
        assert result is True
        
        # Should fail with massive context
        huge_context = {"user_input": "Very long text " * 10000}
        result = token_manager.check_token_limits(huge_context)
        assert result is False
    
    def test_token_manager_get_breakdown(self, token_manager, sample_context):
        """Test getting token breakdown."""
        token_manager.estimate_context_tokens(sample_context)
        breakdown = token_manager.get_token_breakdown()
        
        assert isinstance(breakdown, dict)
        assert "total_tokens" in breakdown
        assert "system_tokens" in breakdown
        assert "available_tokens" in breakdown
    
    def test_token_manager_optimize_context(self, token_manager, sample_context):
        """Test context optimization for token limits."""
        # Create oversized context
        large_context = sample_context.copy()
        large_context["memory"] = "Very long memory content " * 1000
        
        optimized = token_manager.optimize_context(large_context)
        
        assert isinstance(optimized, dict)
        # Should be smaller than original
        original_tokens = token_manager.estimate_context_tokens(large_context)
        optimized_tokens = token_manager.estimate_context_tokens(optimized)
        assert optimized_tokens <= original_tokens
    
    def test_token_manager_reserve_tokens(self, token_manager):
        """Test token reservation functionality."""
        original_available = token_manager.available_tokens
        
        token_manager.reserve_tokens(100)
        
        assert token_manager.available_tokens == original_available - 100
        assert token_manager.reserved_tokens >= 100
    
    def test_token_manager_release_tokens(self, token_manager):
        """Test token release functionality."""
        token_manager.reserve_tokens(100)
        original_available = token_manager.available_tokens
        
        token_manager.release_tokens(50)
        
        assert token_manager.available_tokens == original_available + 50
    
    def test_token_manager_set_model(self, token_manager):
        """Test changing model configuration."""
        token_manager.set_model("claude-3", max_tokens=8192)
        
        assert token_manager.model_name == "claude-3"
        assert token_manager.max_tokens == 8192


class TestContextOptimization:
    """Test context optimization functions."""
    
    def test_optimize_context_for_tokens_basic(self, sample_context):
        """Test basic context optimization."""
        target_tokens = 500
        
        optimized = optimize_context_for_tokens(sample_context, target_tokens)
        
        assert isinstance(optimized, dict)
        assert "user_input" in optimized  # Should preserve user input
        
        # Estimate tokens to verify optimization
        optimized_tokens = estimate_tokens(str(optimized))
        assert optimized_tokens <= target_tokens * 1.1  # Allow 10% tolerance
    
    def test_optimize_context_priority_preservation(self, sample_context):
        """Test that high-priority elements are preserved."""
        target_tokens = 100  # Very small limit
        
        optimized = optimize_context_for_tokens(sample_context, target_tokens)
        
        # System and user input should always be preserved
        assert "system" in optimized or len(optimized.get("system", "")) > 0
        assert "user_input" in optimized
        assert len(optimized["user_input"]) > 0
    
    def test_optimize_context_memory_truncation(self):
        """Test memory truncation during optimization."""
        context_with_long_memory = {
            "system": "System prompt",
            "memory": "Very long memory content that should be truncated " * 100,
            "user_input": "User input to preserve"
        }
        
        target_tokens = 200
        optimized = optimize_context_for_tokens(context_with_long_memory, target_tokens)
        
        # Memory should be truncated
        assert len(optimized["memory"]) < len(context_with_long_memory["memory"])
        # But user input preserved
        assert optimized["user_input"] == context_with_long_memory["user_input"]
    
    def test_optimize_context_canon_reduction(self):
        """Test canon content reduction during optimization."""
        context_with_long_canon = {
            "system": "System prompt",
            "canon": ["Long canon entry " * 50 for _ in range(20)],
            "user_input": "User input"
        }
        
        target_tokens = 300
        optimized = optimize_context_for_tokens(context_with_long_canon, target_tokens)
        
        # Canon should be reduced
        if "canon" in optimized:
            if isinstance(optimized["canon"], list):
                assert len(optimized["canon"]) <= len(context_with_long_canon["canon"])
    
    def test_optimize_context_impossible_target(self, sample_context):
        """Test optimization with impossible token targets."""
        target_tokens = 10  # Impossibly small
        
        optimized = optimize_context_for_tokens(sample_context, target_tokens)
        
        # Should still return something minimal but functional
        assert isinstance(optimized, dict)
        assert "user_input" in optimized


class TestModelLimits:
    """Test model limit management."""
    
    def test_get_model_limits_known_models(self):
        """Test getting limits for known models."""
        models = ["gpt-4", "gpt-3.5-turbo", "claude-3", "claude-2"]
        
        for model in models:
            limits = get_model_limits(model)
            
            assert isinstance(limits, dict)
            assert "max_tokens" in limits
            assert "context_window" in limits
            assert limits["max_tokens"] > 0
    
    def test_get_model_limits_unknown_model(self):
        """Test getting limits for unknown model."""
        limits = get_model_limits("unknown-model")
        
        # Should return default limits
        assert isinstance(limits, dict)
        assert "max_tokens" in limits
        assert limits["max_tokens"] > 0
    
    def test_get_model_limits_caching(self):
        """Test that model limits are cached."""
        # Call twice for same model
        limits1 = get_model_limits("gpt-4")
        limits2 = get_model_limits("gpt-4")
        
        # Should be identical (from cache)
        assert limits1 == limits2


class TestTokenUsageCalculation:
    """Test token usage calculation."""
    
    def test_calculate_token_usage_basic(self):
        """Test basic token usage calculation."""
        prompt = "This is a test prompt"
        response = "This is a test response"
        
        usage = calculate_token_usage(prompt, response)
        
        assert isinstance(usage, dict)
        assert "prompt_tokens" in usage
        assert "response_tokens" in usage
        assert "total_tokens" in usage
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["response_tokens"]
    
    def test_calculate_token_usage_with_model(self):
        """Test token usage calculation with specific model."""
        prompt = "Test prompt"
        response = "Test response"
        
        usage = calculate_token_usage(prompt, response, model="gpt-4")
        
        assert "model" in usage
        assert usage["model"] == "gpt-4"
    
    def test_calculate_token_usage_empty_inputs(self):
        """Test token usage calculation with empty inputs."""
        usage = calculate_token_usage("", "")
        
        assert usage["prompt_tokens"] == 0
        assert usage["response_tokens"] == 0
        assert usage["total_tokens"] == 0
    
    def test_calculate_token_usage_cost_estimation(self):
        """Test token usage with cost estimation."""
        prompt = "This is a longer prompt for cost testing"
        response = "This is a longer response for cost testing"
        
        usage = calculate_token_usage(prompt, response, include_cost=True)
        
        assert "estimated_cost" in usage
        assert isinstance(usage["estimated_cost"], (int, float))
        assert usage["estimated_cost"] >= 0


class TestTokenLimitError:
    """Test TokenLimitError exception."""
    
    def test_token_limit_error_creation(self):
        """Test creating TokenLimitError."""
        error = TokenLimitError("Token limit exceeded", limit=1000, actual=1500)
        
        assert str(error) == "Token limit exceeded"
        assert error.limit == 1000
        assert error.actual == 1500
    
    def test_token_limit_error_without_details(self):
        """Test creating TokenLimitError without details."""
        error = TokenLimitError("Simple error")
        
        assert str(error) == "Simple error"
        assert error.limit is None
        assert error.actual is None


class TestAdvancedTokenManagement:
    """Test advanced token management features."""
    
    def test_adaptive_context_sizing(self, token_manager):
        """Test adaptive context sizing based on available tokens."""
        # Start with large context
        large_context = {
            "system": "System prompt",
            "memory": "Long memory " * 500,
            "canon": "Long canon " * 300,
            "user_input": "User input"
        }
        
        # Should adaptively size based on available tokens
        optimized = token_manager.adaptive_context_sizing(large_context)
        
        assert isinstance(optimized, dict)
        optimized_tokens = token_manager.estimate_context_tokens(optimized)
        assert optimized_tokens <= token_manager.available_tokens
    
    def test_token_efficient_summarization(self, token_manager):
        """Test token-efficient content summarization."""
        long_content = "This is a very long piece of content that needs to be summarized. " * 100
        
        summarized = token_manager.summarize_for_tokens(long_content, target_tokens=50)
        
        assert isinstance(summarized, str)
        assert len(summarized) < len(long_content)
        summary_tokens = estimate_tokens(summarized)
        assert summary_tokens <= 60  # Allow some tolerance
    
    def test_progressive_context_reduction(self, token_manager):
        """Test progressive context reduction strategy."""
        context = {
            "system": "System prompt",
            "memory": "Memory content " * 200,
            "canon": "Canon content " * 150,
            "recent_events": "Recent events " * 100,
            "user_input": "User input"
        }
        
        # Test reduction at different levels
        reduced_90 = token_manager.reduce_context(context, reduction_factor=0.9)
        reduced_50 = token_manager.reduce_context(context, reduction_factor=0.5)
        
        tokens_90 = token_manager.estimate_context_tokens(reduced_90)
        tokens_50 = token_manager.estimate_context_tokens(reduced_50)
        
        assert tokens_50 < tokens_90
        # User input should always be preserved
        assert reduced_50["user_input"] == context["user_input"]
    
    @pytest.mark.asyncio
    async def test_streaming_token_tracking(self, token_manager):
        """Test token tracking for streaming responses."""
        chunks = ["First chunk", "Second chunk", "Third chunk"]
        
        tracker = token_manager.create_streaming_tracker()
        
        for chunk in chunks:
            await tracker.add_chunk(chunk)
        
        final_usage = tracker.get_final_usage()
        
        assert "total_tokens" in final_usage
        assert "chunks_processed" in final_usage
        assert final_usage["chunks_processed"] == 3


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    def test_token_caching(self, token_manager):
        """Test token estimation caching."""
        text = "This is a test text for caching"
        
        # First call should calculate
        tokens1 = token_manager.estimate_tokens_cached(text)
        
        # Second call should use cache
        tokens2 = token_manager.estimate_tokens_cached(text)
        
        assert tokens1 == tokens2
        assert text in token_manager._token_cache
    
    def test_batch_token_estimation(self, token_manager):
        """Test batch token estimation for efficiency."""
        texts = [
            "First text for batch processing",
            "Second text for batch processing", 
            "Third text for batch processing"
        ]
        
        batch_results = token_manager.estimate_tokens_batch(texts)
        
        assert isinstance(batch_results, list)
        assert len(batch_results) == len(texts)
        assert all(isinstance(tokens, int) for tokens in batch_results)
    
    def test_memory_efficient_processing(self, token_manager):
        """Test memory-efficient processing of large contexts."""
        # Create very large context
        huge_context = {
            "system": "System",
            "memory": "Large memory content " * 10000,
            "user_input": "User input"
        }
        
        # Should handle without memory issues
        optimized = token_manager.memory_efficient_optimize(huge_context, target_tokens=1000)
        
        assert isinstance(optimized, dict)
        assert "user_input" in optimized


if __name__ == "__main__":
    pytest.main([__file__])
