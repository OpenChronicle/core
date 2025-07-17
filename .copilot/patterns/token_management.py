"""
Token Management Patterns for OpenChronicle

This module demonstrates patterns for managing tokens across different LLM providers,
implementing scene continuation strategies, and optimizing context usage.
"""

import tiktoken
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

class TokenizerType(Enum):
    """Supported tokenizer types"""
    TIKTOKEN = "tiktoken"
    LLAMA = "llama"
    ANTHROPIC = "anthropic"
    GENERIC = "generic"

@dataclass
class TokenLimits:
    """Token limits for a model"""
    max_context: int
    max_response: int
    safety_margin: int = 100
    
    @property
    def effective_context(self) -> int:
        """Context limit minus safety margin"""
        return self.max_context - self.safety_margin
    
    @property
    def effective_response(self) -> int:
        """Response limit minus safety margin"""
        return self.max_response - self.safety_margin

@dataclass
class TokenUsage:
    """Token usage statistics"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_used: str
    
    @property
    def cost_estimate(self) -> float:
        """Estimate cost based on token usage"""
        # This would be populated based on model pricing
        return 0.0

class TokenManager:
    """
    Manages token counting and optimization across different LLM providers.
    
    Handles:
    - Token counting for different tokenizers
    - Context trimming and optimization
    - Scene continuation detection
    - Multi-part response stitching
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger = logging.getLogger(f"TokenManager_{model_name}")
        
        # Initialize tokenizer based on model
        self.tokenizer = self._get_tokenizer(model_name)
        self.token_limits = self._get_token_limits(model_name)
        
        # Track usage
        self.usage_history: List[TokenUsage] = []
        self.current_session_tokens = 0
    
    def _get_tokenizer(self, model_name: str):
        """Get appropriate tokenizer for model"""
        if model_name.startswith("gpt"):
            return tiktoken.encoding_for_model(model_name)
        elif model_name.startswith("claude"):
            # Would use Anthropic's tokenizer
            return None  # Placeholder
        elif model_name.startswith("llama"):
            # Would use Llama tokenizer
            return None  # Placeholder
        else:
            # Generic word-based estimation
            return None
    
    def _get_token_limits(self, model_name: str) -> TokenLimits:
        """Get token limits for model"""
        limits_map = {
            "gpt-4": TokenLimits(8192, 4096),
            "gpt-3.5-turbo": TokenLimits(4096, 2048),
            "claude-3": TokenLimits(200000, 4096),
            "llama3.2:3b": TokenLimits(4096, 2048),
            "llama3.2:1b": TokenLimits(2048, 1024),
        }
        
        return limits_map.get(model_name, TokenLimits(2048, 1024))
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not text:
            return 0
        
        try:
            if self.tokenizer and hasattr(self.tokenizer, 'encode'):
                return len(self.tokenizer.encode(text))
            else:
                # Fallback to word-based estimation
                return len(text.split()) * 1.3  # Rough conversion factor
        except Exception as e:
            self.logger.warning(f"Token counting failed: {e}")
            return len(text.split()) * 1.3
    
    def estimate_response_tokens(self, prompt: str) -> int:
        """Estimate how many tokens the response might use"""
        prompt_tokens = self.count_tokens(prompt)
        
        # Heuristic: response is usually 0.5-2x prompt length
        # Use conservative estimate for planning
        estimated_response = min(
            prompt_tokens * 1.5,
            self.token_limits.max_response
        )
        
        return int(estimated_response)
    
    def optimize_context(
        self,
        user_input: str,
        memory_context: str,
        canon_context: str,
        style_context: str,
        system_prompt: str
    ) -> Tuple[str, str, str, str]:
        """
        Optimize context to fit within token limits.
        
        Priority order:
        1. System prompt (required)
        2. User input (required)
        3. Style context (high priority)
        4. Recent memory (medium priority)
        5. Canon context (can be trimmed)
        6. Older memory (lowest priority)
        """
        
        # Calculate base requirements
        system_tokens = self.count_tokens(system_prompt)
        user_tokens = self.count_tokens(user_input)
        style_tokens = self.count_tokens(style_context)
        
        # Reserve space for response
        estimated_response = self.estimate_response_tokens(user_input)
        
        # Available tokens for context
        available_tokens = (
            self.token_limits.effective_context - 
            system_tokens - 
            user_tokens - 
            style_tokens - 
            estimated_response
        )
        
        self.logger.info(f"Available context tokens: {available_tokens}")
        
        if available_tokens <= 0:
            self.logger.warning("No space for context - using minimal")
            return "", "", style_context, system_prompt
        
        # Optimize memory and canon context
        optimized_memory = self._trim_memory_context(memory_context, available_tokens // 2)
        optimized_canon = self._trim_canon_context(canon_context, available_tokens // 2)
        
        return optimized_memory, optimized_canon, style_context, system_prompt
    
    def _trim_memory_context(self, memory_context: str, max_tokens: int) -> str:
        """Trim memory context to fit token limit"""
        if not memory_context:
            return ""
        
        current_tokens = self.count_tokens(memory_context)
        if current_tokens <= max_tokens:
            return memory_context
        
        # Split into sections and prioritize recent memories
        sections = memory_context.split("\n\n")
        
        # Keep most recent sections first
        trimmed_sections = []
        used_tokens = 0
        
        for section in sections:
            section_tokens = self.count_tokens(section)
            if used_tokens + section_tokens <= max_tokens:
                trimmed_sections.append(section)
                used_tokens += section_tokens
            else:
                break
        
        result = "\n\n".join(trimmed_sections)
        self.logger.info(f"Trimmed memory context: {current_tokens} -> {self.count_tokens(result)} tokens")
        
        return result
    
    def _trim_canon_context(self, canon_context: str, max_tokens: int) -> str:
        """Trim canon context to fit token limit"""
        if not canon_context:
            return ""
        
        current_tokens = self.count_tokens(canon_context)
        if current_tokens <= max_tokens:
            return canon_context
        
        # Extract most relevant sections (this could be improved with semantic analysis)
        paragraphs = canon_context.split("\n\n")
        
        # Simple approach: keep first paragraphs (usually most important)
        trimmed_paragraphs = []
        used_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)
            if used_tokens + paragraph_tokens <= max_tokens:
                trimmed_paragraphs.append(paragraph)
                used_tokens += paragraph_tokens
            else:
                # Try to fit a summary line
                summary = f"[... additional canon information truncated ...]"
                summary_tokens = self.count_tokens(summary)
                if used_tokens + summary_tokens <= max_tokens:
                    trimmed_paragraphs.append(summary)
                break
        
        result = "\n\n".join(trimmed_paragraphs)
        self.logger.info(f"Trimmed canon context: {current_tokens} -> {self.count_tokens(result)} tokens")
        
        return result
    
    def detect_truncation(self, response: str) -> bool:
        """Detect if response was likely truncated"""
        # Check for common truncation indicators
        truncation_indicators = [
            response.endswith("..."),
            response.endswith(" and"),
            response.endswith(" but"),
            response.endswith(" so"),
            response.endswith(" then"),
            not response.endswith((".", "!", "?", '"', "'")),
            len(response) > 2000 and not response[-50:].count(".") > 0,
        ]
        
        return any(truncation_indicators)
    
    def generate_continuation_prompt(self, original_prompt: str, partial_response: str) -> str:
        """Generate prompt for continuing a truncated response"""
        continuation_prompt = f"""
Continue the following narrative from where it left off. 
Maintain the same tone, style, and character voices.
Do not repeat what has already been written.

Original context (for reference):
{original_prompt[-500:]}  # Last 500 chars for context

Previous response:
{partial_response}

Continue from here:"""
        
        return continuation_prompt
    
    def track_usage(self, usage: TokenUsage) -> None:
        """Track token usage for monitoring"""
        self.usage_history.append(usage)
        self.current_session_tokens += usage.total_tokens
        
        # Log usage
        self.logger.info(f"Token usage: {usage.total_tokens} tokens ({usage.model_used})")
        
        # Check for concerning usage patterns
        if usage.total_tokens > self.token_limits.max_context * 0.8:
            self.logger.warning(f"High token usage: {usage.total_tokens}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get token usage statistics"""
        if not self.usage_history:
            return {"total_tokens": 0, "requests": 0}
        
        total_tokens = sum(usage.total_tokens for usage in self.usage_history)
        total_requests = len(self.usage_history)
        
        models_used = {}
        for usage in self.usage_history:
            models_used[usage.model_used] = models_used.get(usage.model_used, 0) + 1
        
        return {
            "total_tokens": total_tokens,
            "requests": total_requests,
            "average_tokens_per_request": total_tokens / total_requests,
            "models_used": models_used,
            "current_session_tokens": self.current_session_tokens
        }
    
    def reset_session(self) -> None:
        """Reset session token tracking"""
        self.current_session_tokens = 0
        self.logger.info("Token session reset")

class SceneContinuationManager:
    """
    Manages scene continuation when responses are truncated.
    
    Handles:
    - Truncation detection
    - Context building for continuation
    - Multi-part response stitching
    - Scene fragment management
    """
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.logger = logging.getLogger("SceneContinuationManager")
        
        # Track multi-part scenes
        self.scene_fragments: Dict[str, List[str]] = {}
    
    def process_response(
        self,
        scene_id: str,
        response: str,
        original_prompt: str,
        model_adapter
    ) -> Tuple[str, bool]:
        """
        Process response and handle continuation if needed.
        
        Returns:
            Tuple of (final_response, was_continued)
        """
        
        # Check if response was truncated
        if not self.token_manager.detect_truncation(response):
            return response, False
        
        self.logger.info(f"Detected truncation in scene {scene_id}")
        
        # Initialize fragments list if needed
        if scene_id not in self.scene_fragments:
            self.scene_fragments[scene_id] = []
        
        # Add current fragment
        self.scene_fragments[scene_id].append(response)
        
        # Generate continuation
        continuation_prompt = self.token_manager.generate_continuation_prompt(
            original_prompt, response
        )
        
        try:
            # Get continuation from model
            continuation_response = model_adapter.generate_response(
                continuation_prompt,
                max_tokens=self.token_manager.token_limits.max_response // 2
            )
            
            # Add continuation fragment
            self.scene_fragments[scene_id].append(continuation_response.content)
            
            # Check if we need another continuation
            if self.token_manager.detect_truncation(continuation_response.content):
                # Recursive continuation (with depth limit)
                if len(self.scene_fragments[scene_id]) < 5:  # Max 5 fragments
                    return self.process_response(
                        scene_id, 
                        continuation_response.content,
                        continuation_prompt,
                        model_adapter
                    )
                else:
                    self.logger.warning(f"Max continuation depth reached for scene {scene_id}")
            
            # Stitch fragments together
            final_response = self.stitch_fragments(scene_id)
            
            return final_response, True
            
        except Exception as e:
            self.logger.error(f"Continuation failed for scene {scene_id}: {e}")
            return response, False  # Return original truncated response
    
    def stitch_fragments(self, scene_id: str) -> str:
        """Stitch scene fragments together"""
        if scene_id not in self.scene_fragments:
            return ""
        
        fragments = self.scene_fragments[scene_id]
        
        # Simple stitching - just concatenate
        # In practice, this might need more sophisticated merging
        stitched = " ".join(fragments)
        
        # Clean up any obvious duplication at boundaries
        stitched = self._clean_boundaries(stitched)
        
        self.logger.info(f"Stitched {len(fragments)} fragments for scene {scene_id}")
        
        return stitched
    
    def _clean_boundaries(self, text: str) -> str:
        """Clean up text boundaries between fragments"""
        # Remove obvious duplicated sentences at boundaries
        sentences = text.split(". ")
        cleaned_sentences = []
        
        for sentence in sentences:
            if sentence not in cleaned_sentences[-3:]:  # Check last 3 sentences
                cleaned_sentences.append(sentence)
        
        return ". ".join(cleaned_sentences)
    
    def cleanup_scene(self, scene_id: str) -> None:
        """Clean up stored fragments for a scene"""
        if scene_id in self.scene_fragments:
            del self.scene_fragments[scene_id]

# Example usage patterns
class TokenOptimizedContextBuilder:
    """
    Context builder with token optimization.
    
    Demonstrates integration of token management with context building.
    """
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.logger = logging.getLogger("TokenOptimizedContextBuilder")
    
    def build_context(
        self,
        user_input: str,
        memory_manager,
        story_loader,
        style_guide: str
    ) -> str:
        """Build optimized context for LLM prompt"""
        
        # Gather all context components
        system_prompt = self._build_system_prompt(story_loader)
        memory_context = memory_manager.get_context_summary()
        canon_context = story_loader.get_relevant_canon(user_input)
        style_context = style_guide
        
        # Optimize for token limits
        optimized_memory, optimized_canon, style_context, system_prompt = (
            self.token_manager.optimize_context(
                user_input,
                memory_context,
                canon_context,
                style_context,
                system_prompt
            )
        )
        
        # Build final prompt
        prompt_parts = [
            system_prompt,
            f"Style Guide:\n{style_context}",
            f"World Information:\n{optimized_canon}",
            f"Current Context:\n{optimized_memory}",
            f"User Input: {user_input}",
            "Response:"
        ]
        
        final_prompt = "\n\n".join(part for part in prompt_parts if part.strip())
        
        # Log token usage
        token_count = self.token_manager.count_tokens(final_prompt)
        self.logger.info(f"Built context with {token_count} tokens")
        
        return final_prompt
    
    def _build_system_prompt(self, story_loader) -> str:
        """Build system prompt from story metadata"""
        meta = story_loader.get_meta()
        
        system_prompt = f"""
You are a creative writing assistant for an interactive story titled "{meta.get('title', 'Untitled Story')}".

Story Description: {meta.get('description', 'No description provided')}

Your role is to:
1. Continue the narrative based on user input
2. Stay consistent with established characters and world
3. Follow the provided style guide
4. Maintain appropriate tone and pacing
5. Create engaging, immersive content

Respond with narrative content only, no meta-commentary.
"""
        
        return system_prompt.strip()

# Usage example
if __name__ == "__main__":
    # Example usage of token management
    token_manager = TokenManager("gpt-4")
    
    # Example context optimization
    user_input = "I enter the tavern and look around."
    memory_context = "The hero has 100 health and is carrying a sword. They just left the village square."
    canon_context = "The Wanderer's Rest is a cozy tavern..." * 1000  # Long context
    style_context = "Write in third person present tense with rich descriptions."
    system_prompt = "You are a fantasy storyteller..."
    
    optimized = token_manager.optimize_context(
        user_input, memory_context, canon_context, style_context, system_prompt
    )
    
    print(f"Optimized context lengths: {[len(ctx) for ctx in optimized]}")
    
    # Example continuation management
    continuation_manager = SceneContinuationManager(token_manager)
    
    # Simulate truncated response
    truncated_response = "The tavern is warm and inviting. You see patrons sitting at various tables, enjoying their meals and"
    
    # This would normally involve actual model calls
    # final_response, was_continued = continuation_manager.process_response(
    #     "scene_001", truncated_response, "original_prompt", model_adapter
    # )
    
    # Get usage stats
    stats = token_manager.get_usage_stats()
    print(f"Token usage stats: {stats}")
