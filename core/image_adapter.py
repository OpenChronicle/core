"""
Image Generation Adapter - Plugin system for visual storytelling

Provides a unified interface for multiple image generation models including:
- OpenAI DALL-E 2/3
- Stability AI Stable Diffusion
- Local models via APIs
- Custom model integrations

Images are stored as non-critical enhancement content in storypack/images/
"""

import asyncio
import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

import httpx
from PIL import Image
import base64
import io


class ImageProvider(Enum):
    """Supported image generation providers"""
    OPENAI_DALLE = "openai_dalle"
    STABILITY_AI = "stability_ai" 
    LOCAL_SD = "local_sd"
    MOCK = "mock"


class ImageSize(Enum):
    """Standard image sizes for generation"""
    SQUARE_512 = "512x512"
    SQUARE_1024 = "1024x1024"
    PORTRAIT_512 = "512x768"
    LANDSCAPE_768 = "768x512"
    WIDE_1024 = "1024x512"


class ImageType(Enum):
    """Types of images for organization"""
    CHARACTER = "character"
    SCENE = "scene"
    LOCATION = "location"
    ITEM = "item"
    CUSTOM = "custom"


@dataclass
class ImageGenerationRequest:
    """Request for image generation"""
    prompt: str
    image_type: ImageType
    size: ImageSize = ImageSize.SQUARE_512
    character_name: Optional[str] = None
    scene_id: Optional[str] = None
    style_modifiers: Optional[List[str]] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    
    def __post_init__(self):
        """Validate and process request"""
        if self.style_modifiers is None:
            self.style_modifiers = []
            
        # Add default style modifiers based on type
        if self.image_type == ImageType.CHARACTER:
            self.style_modifiers.extend([
                "detailed character portrait",
                "high quality",
                "fantasy art style"
            ])
        elif self.image_type == ImageType.SCENE:
            self.style_modifiers.extend([
                "detailed environment",
                "atmospheric",
                "cinematic composition"
            ])


@dataclass
class ImageGenerationResult:
    """Result of image generation"""
    success: bool
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    cost: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class ImageAdapter(ABC):
    """Abstract base class for image generation adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = ImageProvider(config.get("provider", "mock"))
        self.enabled = config.get("enabled", True)
        
    @abstractmethod
    async def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate an image from the request"""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the adapter is available and configured"""
        pass
        
    def get_provider_name(self) -> str:
        """Get human-readable provider name"""
        return self.provider.value
        
    def supports_size(self, size: ImageSize) -> bool:
        """Check if adapter supports the requested size"""
        # Default implementation supports all sizes
        return True


class OpenAIImageAdapter(ImageAdapter):
    """Adapter for OpenAI DALL-E image generation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.model = config.get("model", "dall-e-3")
        self.quality = config.get("quality", "standard")
        
    def is_available(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(self.api_key and self.enabled)
        
    def supports_size(self, size: ImageSize) -> bool:
        """DALL-E 3 supports specific sizes"""
        if self.model == "dall-e-3":
            return size in [ImageSize.SQUARE_1024, ImageSize.PORTRAIT_512, ImageSize.LANDSCAPE_768]
        return size in [ImageSize.SQUARE_512, ImageSize.SQUARE_1024]
        
    async def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate image using OpenAI DALL-E"""
        if not self.is_available():
            return ImageGenerationResult(
                success=False,
                error_message="OpenAI API key not configured"
            )
            
        if not self.supports_size(request.size):
            return ImageGenerationResult(
                success=False,
                error_message=f"Size {request.size.value} not supported by {self.model}"
            )
            
        start_time = time.time()
        
        try:
            # Build the prompt with style modifiers
            full_prompt = request.prompt
            if request.style_modifiers:
                full_prompt += ", " + ", ".join(request.style_modifiers)
                
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "prompt": full_prompt[:4000],  # DALL-E has prompt limits
                "size": request.size.value,
                "quality": self.quality,
                "n": 1
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers=headers,
                    json=payload
                )
                
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return ImageGenerationResult(
                    success=False,
                    error_message=f"OpenAI API error: {response.status_code} - {error_data.get('error', {}).get('message', 'Unknown error')}"
                )
                
            result_data = response.json()
            image_url = result_data["data"][0]["url"]
            
            # Calculate cost (approximate)
            cost = 0.04 if self.model == "dall-e-3" and self.quality == "standard" else 0.08
            
            return ImageGenerationResult(
                success=True,
                image_url=image_url,
                generation_time=time.time() - start_time,
                cost=cost,
                metadata={
                    "model": self.model,
                    "quality": self.quality,
                    "revised_prompt": result_data["data"][0].get("revised_prompt"),
                    "size": request.size.value
                }
            )
            
        except Exception as e:
            return ImageGenerationResult(
                success=False,
                error_message=f"OpenAI generation failed: {str(e)}",
                generation_time=time.time() - start_time
            )


class MockImageAdapter(ImageAdapter):
    """Mock adapter for testing and development"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    def is_available(self) -> bool:
        """Mock is always available"""
        return self.enabled
        
    async def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate a mock colored square image"""
        start_time = time.time()
        
        # ALWAYS warn when mock image adapter is used
        from utilities.logging_system import log_system_event
        log_system_event("mock_image_adapter_usage", 
                        "WARNING: Mock image adapter generating placeholder image - NOT real AI art!")
        
        try:
            # Simulate generation delay
            await asyncio.sleep(0.5)
            
            # Create a simple colored image based on prompt hash
            prompt_hash = hashlib.md5(request.prompt.encode()).hexdigest()
            color = (
                int(prompt_hash[:2], 16),
                int(prompt_hash[2:4], 16), 
                int(prompt_hash[4:6], 16)
            )
            
            # Parse size
            width, height = map(int, request.size.value.split('x'))
            
            # Create image
            image = Image.new('RGB', (width, height), color)
            
            # Add some text
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(image)
                text = f"MOCK\n{request.image_type.value.upper()}"
                draw.text((10, 10), text, fill=(255, 255, 255))
            except ImportError:
                pass  # Skip text if fonts not available
                
            # Convert to base64 for return
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return ImageGenerationResult(
                success=True,
                image_url=f"data:image/png;base64,{image_b64}",
                generation_time=time.time() - start_time,
                cost=0.0,
                metadata={
                    "model": "mock_generator",
                    "color": f"#{prompt_hash[:6]}",
                    "size": request.size.value
                }
            )
            
        except Exception as e:
            return ImageGenerationResult(
                success=False,
                error_message=f"Mock generation failed: {str(e)}",
                generation_time=time.time() - start_time
            )


class ImageAdapterRegistry:
    """Registry for managing image generation adapters"""
    
    def __init__(self):
        self.adapters: Dict[ImageProvider, ImageAdapter] = {}
        self.fallback_order = [
            ImageProvider.OPENAI_DALLE,
            ImageProvider.STABILITY_AI,
            ImageProvider.LOCAL_SD,
            ImageProvider.MOCK
        ]
        
    def register_adapter(self, adapter: ImageAdapter):
        """Register an image adapter"""
        self.adapters[adapter.provider] = adapter
        
    def get_adapter(self, provider: ImageProvider) -> Optional[ImageAdapter]:
        """Get specific adapter by provider"""
        return self.adapters.get(provider)
        
    def get_available_adapters(self) -> List[ImageAdapter]:
        """Get all available and enabled adapters"""
        return [
            adapter for adapter in self.adapters.values()
            if adapter.is_available()
        ]
        
    def get_best_adapter(self, request: ImageGenerationRequest) -> Optional[ImageAdapter]:
        """Get the best available adapter for a request"""
        for provider in self.fallback_order:
            adapter = self.adapters.get(provider)
            if adapter and adapter.is_available() and adapter.supports_size(request.size):
                return adapter
        return None
        
    async def generate_image(self, request: ImageGenerationRequest, 
                           preferred_provider: Optional[ImageProvider] = None) -> ImageGenerationResult:
        """Generate image with automatic fallback"""
        
        # Try preferred provider first
        if preferred_provider:
            adapter = self.get_adapter(preferred_provider)
            if adapter and adapter.is_available() and adapter.supports_size(request.size):
                result = await adapter.generate_image(request)
                if result.success:
                    return result
                    
        # Try fallback adapters
        adapter = self.get_best_adapter(request)
        if adapter:
            return await adapter.generate_image(request)
            
        return ImageGenerationResult(
            success=False,
            error_message="No available image generation adapters"
        )


def create_image_registry(config: Dict[str, Any]) -> ImageAdapterRegistry:
    """Create and configure image adapter registry"""
    registry = ImageAdapterRegistry()
    
    # Register adapters based on config
    adapters_config = config.get("image_adapters", {})
    
    # OpenAI DALL-E
    if "openai" in adapters_config:
        openai_config = adapters_config["openai"].copy()
        openai_config["provider"] = ImageProvider.OPENAI_DALLE.value
        registry.register_adapter(OpenAIImageAdapter(openai_config))
        
    # Always register mock adapter for fallback
    mock_config = adapters_config.get("mock", {"enabled": True})
    mock_config["provider"] = ImageProvider.MOCK.value
    registry.register_adapter(MockImageAdapter(mock_config))
    
    return registry


# Example usage and testing
if __name__ == "__main__":
    async def test_image_generation():
        """Test the image generation system"""
        
        # Create mock config
        config = {
            "image_adapters": {
                "mock": {"enabled": True},
                "openai": {
                    "enabled": True,
                    "model": "dall-e-3",
                    "quality": "standard"
                }
            }
        }
        
        # Create registry
        registry = create_image_registry(config)
        
        # Test request
        request = ImageGenerationRequest(
            prompt="A wise old wizard reading ancient scrolls in a candlelit library",
            image_type=ImageType.CHARACTER,
            size=ImageSize.SQUARE_512,
            character_name="Gandalf"
        )
        
        # Generate image
        result = await registry.generate_image(request)
        
        print(f"Generation successful: {result.success}")
        if result.success:
            print(f"Generation time: {result.generation_time:.2f}s")
            print(f"Cost: ${result.cost:.4f}")
            print(f"Metadata: {result.metadata}")
        else:
            print(f"Error: {result.error_message}")
            
    # Run test
    asyncio.run(test_image_generation())
