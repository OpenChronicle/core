"""
Image Generation Engine - Visual storytelling enhancement for OpenChronicle

Manages image generation for characters, scenes, and locations with:
- Automatic image directory management in storypacks
- Metadata tracking and organization
- Integration with existing story systems
- Configurable generation triggers
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import httpx
from PIL import Image

try:
    from .image_adapter import (
        ImageAdapterRegistry, ImageGenerationRequest, ImageGenerationResult,
        ImageProvider, ImageSize, ImageType, create_image_registry
    )
except ImportError:
    # For standalone testing
    from image_adapter import (
        ImageAdapterRegistry, ImageGenerationRequest, ImageGenerationResult,
        ImageProvider, ImageSize, ImageType, create_image_registry
    )


logger = logging.getLogger(__name__)


def load_model_registry() -> Dict[str, Any]:
    """Load the model registry configuration."""
    config_path = Path(__file__).parent.parent / "config" / "model_registry.json"
    
    if not config_path.exists():
        return {"default_image_model": "mock_image", "image_fallback_chain": ["mock_image"]}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading model registry: {e}")
        return {"default_image_model": "mock_image", "image_fallback_chain": ["mock_image"]}


def get_image_config_from_registry(story_path: str) -> Dict[str, Any]:
    """Get image configuration from the model registry."""
    registry = load_model_registry()
    
    # Get image models from registry
    image_models = {}
    for model in registry.get("models", []):
        if model.get("name") in ["openai_dalle", "stability_ai", "mock_image"]:
            image_models[model["name"]] = model
    
    # Build adapter configuration
    adapters = {}
    fallback_chain = registry.get("image_fallback_chain", ["mock_image"])
    
    for model_name in fallback_chain:
        if model_name == "openai_dalle":
            adapters["openai"] = {"enabled": True, "class": "OpenAIImageAdapter"}
        elif model_name == "stability_ai":
            adapters["stability"] = {"enabled": False, "class": "StabilityImageAdapter"}  # Disabled by default
        elif model_name == "mock_image":
            adapters["mock"] = {"enabled": True, "class": "MockImageAdapter"}
    
    return {
        "enabled": True,
        "adapters": adapters,
        "auto_generate": {
            "character_portraits": True,
            "scene_images": True,
            "scene_triggers": ["major_event", "new_location"]
        },
        "fallback_chain": fallback_chain,
        "default_model": registry.get("default_image_model", "mock_image")
    }


@dataclass
class ImageMetadata:
    """Metadata for generated images"""
    image_id: str
    filename: str
    image_type: ImageType
    prompt: str
    character_name: Optional[str]
    scene_id: Optional[str]
    provider: str
    model: str
    size: str
    generation_time: float
    cost: float
    timestamp: str
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['image_type'] = self.image_type.value if isinstance(self.image_type, ImageType) else self.image_type
        return data


class ImageGenerationEngine:
    """Main engine for managing image generation in stories"""
    
    def __init__(self, story_path: str, config: Dict[str, Any]):
        self.story_path = Path(story_path)
        self.images_path = self.story_path / "images"
        self.metadata_file = self.images_path / "images.json"
        self.config = config
        
        # Initialize adapter registry
        self.registry = create_image_registry(config)
        
        # Engine settings
        self.auto_generate = config.get("auto_generate", {})
        self.naming_config = config.get("naming", {
            "character_prefix": "char",
            "scene_prefix": "scene", 
            "location_prefix": "loc",
            "item_prefix": "item",
            "custom_prefix": "img"
        })
        
        # Create images directory
        self.images_path.mkdir(exist_ok=True)
        
        # Load existing metadata
        self.metadata = self._load_metadata()
        
        # Statistics
        self.stats = {
            "images_generated": 0,
            "total_cost": 0.0,
            "generation_time": 0.0,
            "providers_used": set()
        }
        
    def _load_metadata(self) -> Dict[str, ImageMetadata]:
        """Load image metadata from JSON file"""
        if not self.metadata_file.exists():
            return {}
            
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            metadata = {}
            for image_id, meta_dict in data.items():
                # Convert dict back to ImageMetadata
                meta_dict['image_type'] = ImageType(meta_dict['image_type'])
                metadata[image_id] = ImageMetadata(**meta_dict)
                
            logger.info(f"Loaded metadata for {len(metadata)} images")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load image metadata: {e}")
            return {}
            
    def _save_metadata(self):
        """Save image metadata to JSON file"""
        try:
            data = {
                image_id: meta.to_dict() 
                for image_id, meta in self.metadata.items()
            }
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save image metadata: {e}")
            
    def _generate_filename(self, image_type: ImageType, name: Optional[str] = None,
                          scene_id: Optional[str] = None, extension: str = "png") -> str:
        """Generate filename for image based on type and context"""
        
        prefix = self.naming_config.get(f"{image_type.value}_prefix", "img")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if image_type == ImageType.CHARACTER and name:
            # char-aletha-20250718_143022.png
            safe_name = "".join(c for c in name.lower() if c.isalnum() or c in '-_')
            return f"{prefix}-{safe_name}-{timestamp}.{extension}"
            
        elif image_type == ImageType.SCENE and scene_id:
            # scene-000123-20250718_143022.png
            return f"{prefix}-{scene_id}-{timestamp}.{extension}"
            
        else:
            # Generic naming
            return f"{prefix}-{timestamp}.{extension}"
            
    def _generate_image_id(self, image_type: ImageType, name: Optional[str] = None) -> str:
        """Generate unique image ID"""
        base = f"{image_type.value}"
        if name:
            base += f"_{name}"
        timestamp = int(time.time() * 1000)
        return f"{base}_{timestamp}"
        
    async def generate_image(self, 
                           prompt: str,
                           image_type: ImageType,
                           character_name: Optional[str] = None,
                           scene_id: Optional[str] = None,
                           size: ImageSize = ImageSize.SQUARE_512,
                           style_modifiers: Optional[List[str]] = None,
                           preferred_provider: Optional[ImageProvider] = None,
                           tags: Optional[List[str]] = None) -> Optional[str]:
        """
        Generate an image and save it to the story's images directory
        
        Returns:
            Image ID if successful, None if failed
        """
        
        if tags is None:
            tags = []
            
        # Create generation request
        request = ImageGenerationRequest(
            prompt=prompt,
            image_type=image_type,
            size=size,
            character_name=character_name,
            scene_id=scene_id,
            style_modifiers=style_modifiers
        )
        
        logger.info(f"Generating {image_type.value} image: {prompt[:50]}...")
        
        try:
            # Generate image
            result = await self.registry.generate_image(request, preferred_provider)
            
            if not result.success:
                logger.error(f"Image generation failed: {result.error_message}")
                return None
                
            # Generate filename and ID
            filename = self._generate_filename(image_type, character_name, scene_id)
            image_id = self._generate_image_id(image_type, character_name)
            image_path = self.images_path / filename
            
            # Download and save image
            if result.image_url:
                if result.image_url.startswith("data:"):
                    # Handle base64 data URLs (from mock adapter)
                    import base64
                    header, data = result.image_url.split(",", 1)
                    image_data = base64.b64decode(data)
                    
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                        
                else:
                    # Download from URL
                    async with httpx.AsyncClient() as client:
                        response = await client.get(result.image_url)
                        response.raise_for_status()
                        
                        with open(image_path, 'wb') as f:
                            f.write(response.content)
                            
            # Create metadata
            metadata = ImageMetadata(
                image_id=image_id,
                filename=filename,
                image_type=image_type,
                prompt=prompt,
                character_name=character_name,
                scene_id=scene_id,
                provider=result.metadata.get("model", "unknown") if result.metadata else "unknown",
                model=result.metadata.get("model", "unknown") if result.metadata else "unknown",
                size=size.value,
                generation_time=result.generation_time or 0.0,
                cost=result.cost or 0.0,
                timestamp=datetime.now().isoformat(),
                tags=tags
            )
            
            # Save metadata
            self.metadata[image_id] = metadata
            self._save_metadata()
            
            # Update statistics
            self.stats["images_generated"] += 1
            self.stats["total_cost"] += metadata.cost
            self.stats["generation_time"] += metadata.generation_time
            self.stats["providers_used"].add(metadata.provider)
            
            logger.info(f"Generated image {image_id}: {filename}")
            return image_id
            
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return None
            
    async def generate_character_portrait(self, character_name: str, 
                                        character_data: Dict[str, Any],
                                        size: ImageSize = ImageSize.PORTRAIT_512) -> Optional[str]:
        """Generate a character portrait from character data"""
        
        # Build prompt from character data
        prompt_parts = []
        
        # Basic description
        if "description" in character_data:
            prompt_parts.append(character_data["description"])
            
        # Physical traits
        if "appearance" in character_data:
            appearance = character_data["appearance"]
            if isinstance(appearance, dict):
                for key, value in appearance.items():
                    if value:
                        prompt_parts.append(f"{key}: {value}")
            else:
                prompt_parts.append(str(appearance))
                
        # Personality influences on appearance
        if "personality" in character_data:
            personality = character_data.get("personality", {})
            if "demeanor" in personality:
                prompt_parts.append(f"demeanor: {personality['demeanor']}")
                
        prompt = ", ".join(prompt_parts) if prompt_parts else f"Portrait of {character_name}"
        
        # Character-specific style modifiers
        style_modifiers = [
            "character portrait",
            "detailed face",
            "high quality",
            "fantasy art"
        ]
        
        # Add clothing/style if available
        if "equipment" in character_data or "clothing" in character_data:
            style_modifiers.append("detailed clothing")
            
        tags = ["character", "portrait", character_name.lower()]
        
        return await self.generate_image(
            prompt=prompt,
            image_type=ImageType.CHARACTER,
            character_name=character_name,
            size=size,
            style_modifiers=style_modifiers,
            tags=tags
        )
        
    async def generate_scene_image(self, scene_id: str, scene_data: Dict[str, Any],
                                 context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Generate an image for a scene"""
        
        # Build prompt from scene data
        prompt_parts = []
        
        # Scene description
        if "description" in scene_data:
            prompt_parts.append(scene_data["description"])
            
        # Location/setting
        if "location" in scene_data:
            prompt_parts.append(f"Setting: {scene_data['location']}")
            
        # Time of day/mood
        if "atmosphere" in scene_data:
            prompt_parts.append(scene_data["atmosphere"])
            
        # Add context from memory or previous scenes
        if context and "recent_events" in context:
            prompt_parts.append(f"Context: {context['recent_events']}")
            
        prompt = ", ".join(prompt_parts) if prompt_parts else f"Scene {scene_id}"
        
        style_modifiers = [
            "detailed environment",
            "atmospheric",
            "cinematic composition",
            "fantasy setting"
        ]
        
        tags = ["scene", f"scene_{scene_id}"]
        
        return await self.generate_image(
            prompt=prompt,
            image_type=ImageType.SCENE,
            scene_id=scene_id,
            size=ImageSize.LANDSCAPE_768,
            style_modifiers=style_modifiers,
            tags=tags
        )
        
    def get_image_path(self, image_id: str) -> Optional[Path]:
        """Get the file path for an image"""
        if image_id in self.metadata:
            return self.images_path / self.metadata[image_id].filename
        return None
        
    def get_images_by_character(self, character_name: str) -> List[ImageMetadata]:
        """Get all images for a specific character"""
        return [
            meta for meta in self.metadata.values()
            if meta.character_name and meta.character_name.lower() == character_name.lower()
        ]
        
    def get_images_by_scene(self, scene_id: str) -> List[ImageMetadata]:
        """Get all images for a specific scene"""
        return [
            meta for meta in self.metadata.values()
            if meta.scene_id == scene_id
        ]
        
    def get_images_by_tag(self, tag: str) -> List[ImageMetadata]:
        """Get all images with a specific tag"""
        return [
            meta for meta in self.metadata.values()
            if tag.lower() in [t.lower() for t in meta.tags]
        ]
        
    def delete_image(self, image_id: str) -> bool:
        """Delete an image and its metadata"""
        if image_id not in self.metadata:
            return False
            
        try:
            # Delete file
            image_path = self.get_image_path(image_id)
            if image_path and image_path.exists():
                image_path.unlink()
                
            # Remove metadata
            del self.metadata[image_id]
            self._save_metadata()
            
            logger.info(f"Deleted image {image_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete image {image_id}: {e}")
            return False
            
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        stats = self.stats.copy()
        stats["providers_used"] = list(stats["providers_used"])
        stats["total_images"] = len(self.metadata)
        stats["available_adapters"] = [
            adapter.get_provider_name() 
            for adapter in self.registry.get_available_adapters()
        ]
        return stats
        
    def export_metadata(self) -> Dict[str, Any]:
        """Export all metadata for backup/transfer"""
        return {
            "metadata": {id: meta.to_dict() for id, meta in self.metadata.items()},
            "stats": self.get_engine_stats(),
            "export_timestamp": datetime.now().isoformat()
        }


# Integration functions for the main OpenChronicle system
def create_image_engine(story_id: str, config: Optional[Dict[str, Any]] = None) -> ImageGenerationEngine:
    """Create and configure an image generation engine for a story using model registry"""
    try:
        # Convert story_id to story path - follow the same pattern as other modules
        # Most modules use storage/<story_id> for file storage
        story_path = f"storage/{story_id}"
        
        # Get image configuration from model registry
        image_config = get_image_config_from_registry(story_path)
        
        # Create engine with registry-based configuration
        return ImageGenerationEngine(story_path, image_config)
        
    except Exception as e:
        print(f"Error creating image engine with registry: {e}")
        # Fallback to basic configuration if registry fails
        fallback_config = {
            "enabled": True,
            "adapters": {
                "mock": {
                    "enabled": True,
                    "class": "MockImageAdapter"
                }
            },
            "default_adapter": "mock"
        }
        story_path = f"storage/{story_id}"
        return ImageGenerationEngine(story_path, fallback_config)


async def auto_generate_character_portrait(engine: ImageGenerationEngine,
                                         character_name: str,
                                         character_data: Dict[str, Any]) -> Optional[str]:
    """Auto-generate character portrait if enabled"""
    if not engine.auto_generate.get("character_portraits", False):
        return None
        
    # Check if character already has a portrait
    existing = engine.get_images_by_character(character_name)
    if any(img.image_type == ImageType.CHARACTER for img in existing):
        logger.info(f"Character {character_name} already has a portrait")
        return None
        
    return await engine.generate_character_portrait(character_name, character_data)


async def auto_generate_scene_image(engine: ImageGenerationEngine,
                                   scene_id: str,
                                   scene_data: Dict[str, Any],
                                   context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Auto-generate scene image if conditions are met"""
    if not engine.auto_generate.get("scene_images", False):
        return None
        
    # Check for trigger conditions
    triggers = engine.auto_generate.get("scene_triggers", ["major_event", "new_location"])
    
    # Simple trigger detection (can be enhanced)
    should_generate = False
    if "major_event" in triggers and scene_data.get("importance", "normal") == "high":
        should_generate = True
    if "new_location" in triggers and scene_data.get("new_location", False):
        should_generate = True
        
    if not should_generate:
        return None
        
    return await engine.generate_scene_image(scene_id, scene_data, context)


# Example usage
if __name__ == "__main__":
    async def test_image_engine():
        """Test the image generation engine"""
        
        # Mock story path
        story_path = "test_story"
        os.makedirs(story_path, exist_ok=True)
        
        # Test config
        config = {
            "image_adapters": {
                "mock": {"enabled": True}
            },
            "auto_generate": {
                "character_portraits": True,
                "scene_images": False
            }
        }
        
        # Create engine
        engine = create_image_engine(story_path, config)
        
        # Test character portrait generation
        character_data = {
            "description": "A wise old wizard with a long white beard",
            "appearance": {
                "hair": "long white beard",
                "eyes": "twinkling blue",
                "clothing": "elaborate robes"
            }
        }
        
        image_id = await engine.generate_character_portrait("Gandalf", character_data)
        print(f"Generated character portrait: {image_id}")
        
        # Test scene generation
        scene_data = {
            "description": "A grand library filled with ancient tomes",
            "location": "The Great Library of Alexandria",
            "atmosphere": "mystical, golden light filtering through tall windows"
        }
        
        scene_image_id = await engine.generate_scene_image("scene_001", scene_data)
        print(f"Generated scene image: {scene_image_id}")
        
        # Print stats
        stats = engine.get_engine_stats()
        print(f"Engine stats: {stats}")
        
        # Cleanup
        import shutil
        shutil.rmtree(story_path, ignore_errors=True)
        
    asyncio.run(test_image_engine())
