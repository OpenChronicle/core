"""
Anthropic Claude adapter implementation.

Another example of the template pattern reducing adapter code from ~100 to ~30 lines.
Shows consistency across different API providers.
"""

from typing import Any
from ..base import BaseAPIAdapter
from ..exceptions import AdapterResponseError


class AnthropicAdapter(BaseAPIAdapter):
    """Anthropic Claude adapter using template method pattern."""
    
    def get_provider_name(self) -> str:
        return "anthropic"
    
    def requires_api_key(self) -> bool:
        return True
    
    def get_api_key_env_var(self) -> str:
        return "ANTHROPIC_API_KEY"
    
    def get_base_url_env_var(self) -> str:
        return "ANTHROPIC_BASE_URL"
    
    def get_default_base_url(self) -> str:
        return "https://api.anthropic.com"
    
    async def _create_client(self) -> Any:
        """Create Anthropic client."""
        import anthropic
        return anthropic.AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Anthropic Claude API."""
        if not self.initialized or not self.client:
            raise RuntimeError("Adapter not initialized")
        
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text content from the response
            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            return ""
            
        except Exception as e:
            raise AdapterResponseError(self.provider_name, f"Anthropic generation failed: {e}")
