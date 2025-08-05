# OpenChronicle Development Guidelines

## Code Style and Conventions

### Python Code Standards
- **PEP 8**: Follow Python PEP 8 style guide
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Google-style docstrings for all classes and functions
- **Error Handling**: Explicit error handling with logging
- **Imports**: Group imports (stdlib, third-party, local) with blank lines

### Example Function Structure
```python
def process_scene_input(
    user_input: str,
    story_id: str,
    memory_context: Dict[str, Any],
    model_config: Optional[ModelConfig] = None
) -> SceneResult:
    """
    Process user input to generate scene content.
    
    Args:
        user_input: Raw user input text
        story_id: Unique identifier for the story
        memory_context: Current memory state
        model_config: Optional model configuration override
    
    Returns:
        SceneResult containing generated content and metadata
    
    Raises:
        ValidationError: If input validation fails
        ModelError: If LLM generation fails
    """
    logger = get_logger(f"scene_processor_{story_id}")
    
    try:
        # Validate input
        if not user_input.strip():
            raise ValidationError("Empty user input")
        
        # Process input
        logger.info(f"Processing scene input for story {story_id}")
        
        # Implementation here
        
        return SceneResult(
            content=generated_content,
            metadata=scene_metadata,
            tokens_used=token_count
        )
        
    except Exception as e:
        logger.error(f"Scene processing failed: {e}")
        raise
```

### Class Structure Pattern
```python
@dataclass
class ModuleConfig:
    """Configuration for the module"""
    enabled: bool = True
    debug_mode: bool = False

class ModuleBase:
    """Base class for OpenChronicle modules"""
    
    def __init__(self, story_id: str, config: Optional[ModuleConfig] = None):
        self.story_id = story_id
        self.config = config or ModuleConfig()
        self.logger = get_logger(f"{self.__class__.__name__}_{story_id}")
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the module"""
        if self._initialized:
            return
        
        # Initialization logic
        self._initialized = True
        self.logger.info("Module initialized")
    
    def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Module cleanup complete")
```

## Database Patterns

### Database Operations
- Always use parameterized queries
- Handle database errors gracefully
- Use transactions for multi-step operations
- Include proper indexing for performance

### Example Database Pattern
```python
def store_scene_data(self, scene_id: str, data: Dict[str, Any]) -> None:
    """Store scene data with proper error handling"""
    try:
        with self.db_manager.transaction():
            self.db_manager.execute_query("""
                INSERT OR REPLACE INTO scenes 
                (scene_id, content, memory_snapshot, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (scene_id, data['content'], json.dumps(data['memory'])))
            
            # Update related tables
            self._update_scene_metadata(scene_id, data)
            
    except sqlite3.Error as e:
        self.logger.error(f"Database error storing scene {scene_id}: {e}")
        raise DatabaseError(f"Failed to store scene: {e}")
```

## Error Handling Guidelines

### Custom Exception Classes
```python
class OpenChronicleError(Exception):
    """Base exception for OpenChronicle"""
    pass

class ValidationError(OpenChronicleError):
    """Raised when input validation fails"""
    pass

class ModelError(OpenChronicleError):
    """Raised when LLM model operations fail"""
    pass

class DatabaseError(OpenChronicleError):
    """Raised when database operations fail"""
    pass
```

### Error Handling Pattern
```python
def risky_operation(self, data: Any) -> Result:
    """Example of proper error handling"""
    try:
        # Validate inputs
        if not self._validate_input(data):
            raise ValidationError("Invalid input data")
        
        # Perform operation
        result = self._perform_operation(data)
        
        # Log success
        self.logger.info("Operation completed successfully")
        return result
        
    except ValidationError:
        self.logger.warning("Input validation failed")
        raise  # Re-raise validation errors
        
    except ModelError as e:
        self.logger.error(f"Model operation failed: {e}")
        # Attempt fallback or return default
        return self._fallback_operation(data)
        
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        raise OpenChronicleError(f"Operation failed: {e}")
```

## Testing Guidelines

### Test Structure
- Use pytest for all testing
- Group related tests in classes
- Use fixtures for common setup
- Mock external dependencies
- Test both success and failure cases

### Test Naming Convention
```python
def test_[module]_[function]_[scenario]_[expected_result]():
    """Test naming pattern"""
    pass

# Examples:
def test_memory_manager_store_data_valid_input_success():
def test_scene_logger_log_scene_database_error_raises_exception():
def test_model_adapter_generate_response_api_timeout_uses_fallback():
```

## Configuration Management

### Environment Variables
```python
# Use environment variables for sensitive data
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Provide defaults for optional settings
DEBUG_MODE = os.getenv("OPENCHRONICLE_DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("OPENCHRONICLE_LOG_LEVEL", "INFO")
```

### Configuration Files
```python
@dataclass
class SystemConfig:
    """System-wide configuration"""
    debug_mode: bool = False
    log_level: str = "INFO"
    max_concurrent_stories: int = 10
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'SystemConfig':
        """Load configuration from file"""
        with open(config_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
```

## Logging Standards

### Logger Setup
```python
def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger
```

### Logging Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about program execution
- **WARNING**: Something unexpected happened, but the program can continue
- **ERROR**: A serious problem occurred, but the program can continue
- **CRITICAL**: A very serious error occurred, program may not be able to continue

### Logging Examples
```python
# Good logging practices
self.logger.info(f"Processing story {story_id}")
self.logger.debug(f"Memory context: {memory_context}")
self.logger.warning(f"Model {model_name} not available, using fallback")
self.logger.error(f"Failed to load storypack: {error}")
```

## Performance Guidelines

### Database Performance
- Use appropriate indexes
- Batch database operations when possible
- Use connection pooling for high-volume operations
- Monitor query performance

### Memory Management
- Use generators for large datasets
- Implement caching for frequently accessed data
- Clean up resources in finally blocks or context managers
- Monitor memory usage in long-running processes

### Async Operations
```python
async def process_multiple_scenes(self, scene_inputs: List[str]) -> List[SceneResult]:
    """Process multiple scenes concurrently"""
    tasks = [
        self.process_scene_async(input_text)
        for input_text in scene_inputs
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            self.logger.error(f"Scene processing failed: {result}")
        else:
            valid_results.append(result)
    
    return valid_results
```

## Security Considerations

### Input Validation
```python
def validate_user_input(self, user_input: str) -> bool:
    """Validate user input for security"""
    # Check length
    if len(user_input) > MAX_INPUT_LENGTH:
        return False
    
    # Check for injection attempts
    if any(pattern in user_input.lower() for pattern in SQL_INJECTION_PATTERNS):
        return False
    
    # Check for XSS attempts
    if any(pattern in user_input.lower() for pattern in XSS_PATTERNS):
        return False
    
    return True
```

### Data Sanitization
```python
def sanitize_output(self, output: str) -> str:
    """Sanitize output before displaying"""
    # Remove potentially dangerous content
    sanitized = html.escape(output)
    
    # Additional sanitization rules
    sanitized = re.sub(r'<script.*?</script>', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized
```

## Documentation Standards

### Module Documentation
```python
"""
OpenChronicle Memory Manager

This module handles persistent memory storage and retrieval for stories.
It manages character states, world flags, and scene history.

Example:
    manager = MemoryManager("story_123")
    manager.store_memory("scene_001", {"hero_health": 100})
    memory = manager.get_memory("scene_001")

Classes:
    MemoryManager: Main interface for memory operations
    MemoryConfig: Configuration for memory management
    MemorySnapshot: Immutable memory state at a point in time
"""
```

### API Documentation
```python
def generate_scene_content(
    self,
    user_input: str,
    context: Dict[str, Any],
    model_preference: Optional[str] = None
) -> SceneResult:
    """
    Generate scene content based on user input and context.
    
    This method processes user input through the content analysis pipeline,
    builds appropriate context from memory and canon, and generates
    narrative content using the specified or default LLM model.
    
    Args:
        user_input: The user's input text or command
        context: Current story context including memory and flags
        model_preference: Optional model to use instead of default
    
    Returns:
        SceneResult containing:
            - content: Generated narrative text
            - metadata: Scene metadata (tokens used, model, etc.)
            - memory_updates: Changes to be applied to memory
            - flags: Any new flags or flag changes
    
    Raises:
        ValidationError: If input validation fails
        ModelError: If all configured models fail
        ContextError: If context building fails
    
    Example:
        >>> manager = SceneManager("story_123")
        >>> result = manager.generate_scene_content(
        ...     "I enter the tavern",
        ...     {"current_location": "village_square"}
        ... )
        >>> print(result.content)
        "You push open the heavy wooden door..."
    """
```

## Module Integration Guidelines

### Inter-Module Communication
- Use dependency injection for module dependencies
- Define clear interfaces between modules
- Avoid circular dependencies
- Use event-driven patterns for loose coupling

### Example Integration Pattern
```python
class StoryEngine:
    """Main story processing engine"""
    
    def __init__(self, story_id: str):
        self.story_id = story_id
        
        # Initialize core modules
        self.loader = StoryLoader(story_id)
        self.memory = MemoryManager(story_id)
        self.analyzer = ContentAnalyzer(story_id)
        self.context_builder = ContextBuilder(story_id)
        self.model_adapter = ModelAdapter(story_id)
        self.logger = SceneLogger(story_id)
        
        # Wire up dependencies
        self.context_builder.set_memory_manager(self.memory)
        self.context_builder.set_story_loader(self.loader)
        self.model_adapter.set_content_analyzer(self.analyzer)
    
    def process_input(self, user_input: str) -> SceneResult:
        """Process user input through the full pipeline"""
        # Analyze content
        analysis = self.analyzer.analyze_content(user_input)
        
        # Build context
        context = self.context_builder.build_context(user_input, analysis)
        
        # Generate response
        response = self.model_adapter.generate_response(context)
        
        # Update memory
        self.memory.update_from_scene(response)
        
        # Log scene
        scene_id = self.logger.log_scene(user_input, response)
        
        return SceneResult(
            scene_id=scene_id,
            content=response.content,
            analysis=analysis,
            tokens_used=response.tokens_used
        )
```

Remember: Always prioritize clarity, maintainability, and testability over clever solutions.
