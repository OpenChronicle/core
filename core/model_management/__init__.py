"""
Model Management Package - Unified Core Modules Architecture

This package combines two complementary approaches to create a comprehensive 
model management system that replaces the monolithic ModelManager:

**Foundation Layer (from main branch):**
- BaseAdapter: Template method pattern eliminating 90% of adapter duplication
- AdapterRegistry: Factory pattern for adapter creation and management
- AdapterInterfaces: Common interfaces and type definitions
- AdapterConfig: Configuration management and validation

**Orchestration Layer (from refactor branch):**
- RegistryManager: Configuration and provider management
- ModelOrchestrator: Main coordination and adapter management (~200 lines)
- ContentRouter: Intelligent content-based routing
- HealthMonitor: Comprehensive health checking and performance tracking

**Combined Benefits:**
- Reduce adapter implementation from 100+ lines to 20-30 lines
- Total system: ~1,500 lines vs original 4,473 lines (67% reduction)
- Eliminate code duplication across provider adapters
- Intelligent routing and health monitoring
- Dynamic adapter loading with performance tracking

Usage:
    from core.model_management import ModelOrchestrator, AdapterFactory
    
    # Initialize the unified system
    factory = AdapterFactory()  # Uses base adapters from main
    orchestrator = ModelOrchestrator(factory)  # Uses orchestration from refactor
    
    # Clean API with intelligent routing and health monitoring
    response = await orchestrator.generate_response(prompt, content_type="narrative")
"""

# Foundation layer imports (from main branch)
from .base_adapter import BaseAdapter, BaseAPIAdapter, BaseLocalAdapter
from .adapter_registry import AdapterRegistry, AdapterFactory
from .adapter_interfaces import ModelAdapterInterface, AdapterConfig
from .adapter_config import ConfigValidator, ConfigManager

# Orchestration layer imports (from refactor branch)
from .registry import RegistryManager
from .orchestrator import ModelOrchestrator
from .content_router import ContentRouter, ContentType, ComplexityLevel
from .health_monitor import HealthMonitor, HealthStatus, HealthCheckResult, PerformanceMetrics

# Unified API - ModelOrchestrator uses AdapterFactory internally
ModelManager = ModelOrchestrator

__all__ = [
    # Unified API
    'ModelManager',      # Backward compatibility (ModelOrchestrator)
    
    # Foundation layer (Template Method Pattern)
    'BaseAdapter',
    'BaseAPIAdapter', 
    'BaseLocalAdapter',
    'AdapterRegistry',
    'AdapterFactory',
    'ModelAdapterInterface',
    'AdapterConfig',
    'ConfigValidator',
    'ConfigManager',
    
    # Orchestration layer (Intelligence & Health)
    'RegistryManager',
    'ModelOrchestrator', 
    'ContentRouter',
    'ContentType',
    'ComplexityLevel',
    'HealthMonitor',
    'HealthStatus',
    'HealthCheckResult',
    'PerformanceMetrics'
]

# Unified version - represents the integration of both approaches
__version__ = "2.0.0-unified"
__description__ = "Unified model management combining template method adapters with intelligent orchestration"
__author__ = 'OpenChronicle Core Team'
