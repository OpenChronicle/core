"""
OpenChronicle Performance Monitoring Interfaces Package

Interface definitions for the modular performance monitoring system.
"""

from .performance_interfaces import IMetricsCollector  # Interfaces
from .performance_interfaces import PerformanceMetrics  # Data classes
from .performance_interfaces import (
    BottleneckAnalysis,
    BottleneckReport,
    IAlertManager,
    IBottleneckAnalyzer,
    IMetricsStorage,
    IPerformanceOrchestrator,
    IReportGenerator,
    ITrendAnalyzer,
    MetricsQuery,
    MonitoringContext,
    OperationContext,
    PerformanceReport,
    TrendAnalysis,
)

__all__ = [
    # Data classes
    "PerformanceMetrics",
    "BottleneckAnalysis",
    "BottleneckReport",
    "TrendAnalysis",
    "MetricsQuery",
    "PerformanceReport",
    "MonitoringContext",
    "OperationContext",
    # Interfaces
    "IMetricsCollector",
    "IMetricsStorage",
    "IBottleneckAnalyzer",
    "ITrendAnalyzer",
    "IReportGenerator",
    "IAlertManager",
    "IPerformanceOrchestrator",
]
