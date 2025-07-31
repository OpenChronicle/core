"""
Ollama adapter implementation.

Demonstrates the template pattern working for local API providers.
Original Ollama adapter was ~100 lines, now reduced to ~40 lines.
"""

from typing import Any
from ..base import BaseAPIAdapter
from ..exceptions import AdapterResponseError


class OllamaAdapter(BaseAPIAdapter):
    """Ollama local model adapter using template method pattern."""
    
    def get_provider_name(self) -> str:
        return "ollama"
    
    def requires_api_key(self) -> bool:
        return False  # Ollama doesn't require API keys
    
    def get_api_key_env_var(self) -> str:
        return ""  # Not used for Ollama
    
    def get_base_url_env_var(self) -> str:
        return "OLLAMA_HOST"
    
    def get_default_base_url(self) -> str:
        return "http://localhost:11434"
    
    async def _create_client(self) -> Any:
        """Create HTTP client for Ollama API."""
        import httpx
        timeout = self.config.get('timeout', 30.0)
        client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        
        # Test connection during client creation
        try:
            response = await client.get("/api/tags")
            if response.status_code != 200:
                raise ConnectionError(f"Ollama connection failed: {response.status_code}")
            return client
        except Exception as e:
            await client.aclose()
            raise ConnectionError(f"Failed to connect to Ollama: {e}")
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Ollama API."""
        if not self.initialized or not self.client:
            raise RuntimeError("Adapter not initialized")
        
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens)
                }
            }
            
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except Exception as e:
            # Enhanced error handling for common Ollama issues
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg or "404" in error_msg:
                raise AdapterResponseError(
                    self.provider_name,
                    f"Model '{self.model_name}' not found. Model may have been removed from Ollama server."
                )
            else:
                raise AdapterResponseError(self.provider_name, f"Ollama generation failed: {e}")
    
    async def cleanup(self):
        """Clean up HTTP client resources."""
        if self.client:
            await self.client.aclose()
