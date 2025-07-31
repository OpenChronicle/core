"""
OpenAI adapter implementation.

This adapter demonstrates the massive code reduction achieved through the BaseAPIAdapter
template pattern. The original OpenAI adapter was ~100 lines of mostly duplicated code.
This implementation is only ~30 lines of provider-specific logic.
"""

from typing import Any
from ..base import BaseAPIAdapter
from ..exceptions import AdapterResponseError


class OpenAIAdapter(BaseAPIAdapter):
    """OpenAI GPT adapter using template method pattern."""
    
    def get_provider_name(self) -> str:
        return "openai"
    
    def requires_api_key(self) -> bool:
        return True
    
    def get_api_key_env_var(self) -> str:
        return "OPENAI_API_KEY"
    
    def get_base_url_env_var(self) -> str:
        return "OPENAI_BASE_URL"
    
    def get_default_base_url(self) -> str:
        return "https://api.openai.com/v1"
    
    async def _create_client(self) -> Any:
        """Create OpenAI client - only provider-specific logic needed."""
        import openai
        return openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        if not self.initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a creative storytelling assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                stop=kwargs.get("stop_sequences", None)
            )
            
            content = response.choices[0].message.content
            if content is None:
                return ""
            return content.strip()
            
        except Exception as e:
            raise AdapterResponseError(self.provider_name, f"OpenAI generation failed: {e}")
