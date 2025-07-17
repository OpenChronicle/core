"""
Enhanced Token Management with Dynamic Model Selection
Integrates with the dynamic model plugin system for smart model switching.
"""

import os
import sys
import json
import tiktoken
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_system_event, log_info, log_warning, log_error

class TokenManager:
    """Manages token usage and scene continuation with dynamic model selection."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.token_usage = {}
        self.continuation_cache = {}
        self.encoders = {}
        
    def get_tokenizer(self, model_name: str):
        """Get tokenizer for a specific model."""
        if model_name not in self.encoders:
            try:
                # Try to get model-specific tokenizer
                model_config = self.model_manager.get_adapter_info(model_name)
                provider = model_config.get("provider", "").lower()
                
                if provider == "openai":
                    self.encoders[model_name] = tiktoken.encoding_for_model(
                        model_config.get("model_name", "gpt-4")
                    )
                elif provider == "anthropic":
                    # Use claude tokenizer approximation
                    self.encoders[model_name] = tiktoken.get_encoding("cl100k_base")
                else:
                    # Fallback to general tokenizer
                    self.encoders[model_name] = tiktoken.get_encoding("cl100k_base")
                    
            except Exception as e:
                log_warning(f"Failed to get tokenizer for {model_name}: {e}")
                self.encoders[model_name] = tiktoken.get_encoding("cl100k_base")
                
        return self.encoders[model_name]
    
    def estimate_tokens(self, text: str, model_name: str) -> int:
        """Estimate token count for given text and model."""
        try:
            tokenizer = self.get_tokenizer(model_name)
            return len(tokenizer.encode(text))
        except Exception as e:
            log_error(f"Token estimation failed for {model_name}: {e}")
            # Fallback estimation: ~4 chars per token
            return len(text) // 4
    
    def select_optimal_model_for_length(self, prompt_length: int, response_length: int) -> Optional[str]:
        """Select the best model based on token requirements."""
        total_tokens = prompt_length + response_length
        
        # Get all available models and their token limits
        models = self.model_manager.list_model_configs()
        suitable_models = []
        
        for model_name, config in models.items():
            if not config.get("enabled", True):
                continue
                
            max_tokens = config.get("max_tokens", 4096)
            if total_tokens <= max_tokens * 0.8:  # Leave 20% buffer
                suitable_models.append({
                    "name": model_name,
                    "max_tokens": max_tokens,
                    "cost": config.get("cost_per_token", 0.001),
                    "provider": config.get("provider", "unknown")
                })
        
        if not suitable_models:
            log_warning(f"No models can handle {total_tokens} tokens")
            return None
            
        # Sort by cost efficiency, then by token capacity
        suitable_models.sort(key=lambda x: (x["cost"], -x["max_tokens"]))
        
        selected = suitable_models[0]["name"]
        log_info(f"Selected model {selected} for {total_tokens} tokens")
        return selected
    
    def check_truncation_risk(self, prompt: str, model_name: str, max_response_tokens: int = 2048) -> bool:
        """Check if the prompt + response might exceed model limits."""
        prompt_tokens = self.estimate_tokens(prompt, model_name)
        model_config = self.model_manager.get_adapter_info(model_name)
        max_tokens = model_config.get("max_tokens", 4096)
        
        total_needed = prompt_tokens + max_response_tokens
        return total_needed > max_tokens * 0.9  # 90% threshold
    
    def trim_context_intelligently(self, context_parts: Dict[str, str], 
                                  target_tokens: int, model_name: str) -> Dict[str, str]:
        """Trim context parts to fit within token limits."""
        current_tokens = sum(self.estimate_tokens(part, model_name) 
                           for part in context_parts.values())
        
        if current_tokens <= target_tokens:
            return context_parts
            
        # Priority order for trimming (keep most important)
        trim_order = ["canon", "memory", "style", "recent_scenes"]
        trimmed_parts = context_parts.copy()
        
        for part_name in trim_order:
            if part_name in trimmed_parts and current_tokens > target_tokens:
                original_text = trimmed_parts[part_name]
                original_tokens = self.estimate_tokens(original_text, model_name)
                
                # Trim to 70% of original length
                trim_ratio = 0.7
                trimmed_length = int(len(original_text) * trim_ratio)
                trimmed_parts[part_name] = original_text[:trimmed_length] + "..."
                
                new_tokens = self.estimate_tokens(trimmed_parts[part_name], model_name)
                current_tokens = current_tokens - original_tokens + new_tokens
                
                log_info(f"Trimmed {part_name}: {original_tokens} -> {new_tokens} tokens")
        
        return trimmed_parts
    
    def detect_truncation(self, response: str) -> bool:
        """Detect if a response was likely truncated."""
        # Check for common truncation indicators
        truncation_indicators = [
            # Incomplete sentences
            response.endswith((' ', '  ', ',')),
            # Unfinished quotes
            response.count('"') % 2 == 1,
            response.count("'") % 2 == 1,
            # Incomplete brackets/parentheses
            response.count('(') != response.count(')'),
            response.count('[') != response.count(']'),
            response.count('{') != response.count('}'),
            # Abrupt ending
            len(response) > 100 and not response.strip().endswith(('.', '!', '?', '"', "'"))
        ]
        
        return any(truncation_indicators)
    
    async def continue_scene(self, original_prompt: str, partial_response: str, 
                           story_id: str, model_name: str) -> str:
        """Continue a truncated scene using dynamic model selection."""
        continuation_key = f"{story_id}_{hash(partial_response)}"
        
        if continuation_key in self.continuation_cache:
            return self.continuation_cache[continuation_key]
        
        # Build continuation prompt
        continuation_prompt = f"""Continue this scene exactly where it left off:

Previous content:
{partial_response}

Continue naturally from where it ended, maintaining the same style and tone."""
        
        # Check if current model can handle continuation
        if self.check_truncation_risk(continuation_prompt, model_name):
            # Switch to a model with higher token limit
            continuation_tokens = self.estimate_tokens(continuation_prompt, model_name)
            new_model = self.select_optimal_model_for_length(continuation_tokens, 1024)
            
            if new_model and new_model != model_name:
                log_info(f"Switching from {model_name} to {new_model} for continuation")
                model_name = new_model
        
        try:
            # Generate continuation
            continuation = await self.model_manager.generate_response(
                continuation_prompt,
                adapter_name=model_name,
                story_id=story_id,
                temperature=0.8,
                max_tokens=1024
            )
            
            # Combine responses
            full_response = partial_response + continuation
            self.continuation_cache[continuation_key] = full_response
            
            log_system_event("scene_continuation", 
                           f"Continued scene using {model_name} (+{len(continuation)} chars)")
            
            return full_response
            
        except Exception as e:
            log_error(f"Scene continuation failed: {e}")
            return partial_response
    
    def track_token_usage(self, model_name: str, prompt_tokens: int, 
                         response_tokens: int, cost: float = 0.0):
        """Track token usage per model for monitoring."""
        if model_name not in self.token_usage:
            self.token_usage[model_name] = {
                "prompt_tokens": 0,
                "response_tokens": 0,
                "total_cost": 0.0,
                "requests": 0
            }
        
        usage = self.token_usage[model_name]
        usage["prompt_tokens"] += prompt_tokens
        usage["response_tokens"] += response_tokens
        usage["total_cost"] += cost
        usage["requests"] += 1
        
        log_system_event("token_usage", 
                        f"{model_name}: {prompt_tokens}+{response_tokens} tokens, ${cost:.4f}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get comprehensive token usage statistics."""
        total_stats = {
            "total_prompt_tokens": 0,
            "total_response_tokens": 0,
            "total_cost": 0.0,
            "total_requests": 0,
            "models": self.token_usage.copy()
        }
        
        for model_stats in self.token_usage.values():
            total_stats["total_prompt_tokens"] += model_stats["prompt_tokens"]
            total_stats["total_response_tokens"] += model_stats["response_tokens"]
            total_stats["total_cost"] += model_stats["total_cost"]
            total_stats["total_requests"] += model_stats["requests"]
        
        return total_stats
    
    def recommend_model_switch(self, current_model: str, usage_pattern: Dict[str, Any]) -> Optional[str]:
        """Recommend model switching based on usage patterns."""
        if usage_pattern.get("high_cost", False):
            # Recommend cheaper models
            models = self.model_manager.list_model_configs()
            cheaper_models = [
                name for name, config in models.items()
                if config.get("cost_per_token", 0.001) < 0.0001 and config.get("enabled", True)
            ]
            if cheaper_models:
                return cheaper_models[0]
        
        if usage_pattern.get("frequent_truncation", False):
            # Recommend models with higher token limits
            models = self.model_manager.list_model_configs()
            high_token_models = [
                name for name, config in models.items()
                if config.get("max_tokens", 4096) > 8192 and config.get("enabled", True)
            ]
            if high_token_models:
                return high_token_models[0]
        
        return None
