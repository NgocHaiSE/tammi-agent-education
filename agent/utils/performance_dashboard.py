"""
Performance dashboard logging utility for structured performance metrics.

This module provides utilities to create structured logs that can be easily
parsed by monitoring dashboards like Grafana, Kibana, or custom analytics tools.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from agent.utils.logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of performance metrics."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    RESOURCE_USAGE = "resource_usage"


class ComponentType(Enum):
    """Types of system components."""
    GRPC_HANDLER = "grpc_handler"
    CACHE_BACKEND = "cache_backend"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    SERIALIZATION = "serialization"


@dataclass
class PerformanceMetric:
    """Structured performance metric for dashboard consumption."""
    timestamp: str
    metric_type: str
    component_type: str
    component_name: str
    operation: str
    value: float
    unit: str
    labels: Dict[str, Any]
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class PerformanceBreakdown:
    """Detailed performance breakdown for complex operations."""
    timestamp: str
    operation: str
    total_duration_ms: float
    stages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class PerformanceDashboard:
    """
    Performance dashboard logging utility.
    
    Provides structured logging for performance metrics that can be easily
    consumed by monitoring dashboards and analytics tools.
    """
    
    def __init__(self, service_name: str = "api_gateway"):
        """
        Initialize performance dashboard logger.
        
        Args:
            service_name: Name of the service for metric labeling
        """
        self.service_name = service_name
        self.dashboard_logger = get_logger(f"{__name__}.dashboard")
    
    def log_latency_metric(
        self,
        component_type: ComponentType,
        component_name: str,
        operation: str,
        duration_ms: float,
        labels: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Log latency metric for dashboard consumption.
        
        Args:
            component_type: Type of component (gRPC, cache, etc.)
            component_name: Specific component name
            operation: Operation being measured
            duration_ms: Duration in milliseconds
            labels: Additional labels for filtering/grouping
            trace_id: Request trace ID
            request_id: Request ID
        """
        metric = PerformanceMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.LATENCY.value,
            component_type=component_type.value,
            component_name=component_name,
            operation=operation,
            value=duration_ms,
            unit="milliseconds",
            labels=labels or {},
            trace_id=trace_id,
            request_id=request_id
        )
        
        self.dashboard_logger.info(
            "PERFORMANCE_METRIC",
            extra={
                "metric_data": metric.to_dict(),
                "dashboard_type": "latency",
                "service": self.service_name
            }
        )
    
    def log_throughput_metric(
        self,
        component_type: ComponentType,
        component_name: str,
        operation: str,
        requests_per_second: float,
        labels: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log throughput metric for dashboard consumption.
        
        Args:
            component_type: Type of component
            component_name: Specific component name
            operation: Operation being measured
            requests_per_second: Throughput in requests per second
            labels: Additional labels for filtering/grouping
        """
        metric = PerformanceMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.THROUGHPUT.value,
            component_type=component_type.value,
            component_name=component_name,
            operation=operation,
            value=requests_per_second,
            unit="requests_per_second",
            labels=labels or {}
        )
        
        self.dashboard_logger.info(
            "PERFORMANCE_METRIC",
            extra={
                "metric_data": metric.to_dict(),
                "dashboard_type": "throughput",
                "service": self.service_name
            }
        )
    
    def log_error_rate_metric(
        self,
        component_type: ComponentType,
        component_name: str,
        operation: str,
        error_rate_percent: float,
        labels: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error rate metric for dashboard consumption.
        
        Args:
            component_type: Type of component
            component_name: Specific component name
            operation: Operation being measured
            error_rate_percent: Error rate as percentage (0-100)
            labels: Additional labels for filtering/grouping
        """
        metric = PerformanceMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.ERROR_RATE.value,
            component_type=component_type.value,
            component_name=component_name,
            operation=operation,
            value=error_rate_percent,
            unit="percent",
            labels=labels or {}
        )
        
        self.dashboard_logger.info(
            "PERFORMANCE_METRIC",
            extra={
                "metric_data": metric.to_dict(),
                "dashboard_type": "error_rate",
                "service": self.service_name
            }
        )
    
    def log_cache_hit_rate_metric(
        self,
        cache_backend: str,
        operation: str,
        hit_rate_percent: float,
        labels: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log cache hit rate metric for dashboard consumption.
        
        Args:
            cache_backend: Cache backend name (redis, memory, etc.)
            operation: Cache operation
            hit_rate_percent: Cache hit rate as percentage (0-100)
            labels: Additional labels for filtering/grouping
        """
        metric = PerformanceMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.CACHE_HIT_RATE.value,
            component_type=ComponentType.CACHE_BACKEND.value,
            component_name=cache_backend,
            operation=operation,
            value=hit_rate_percent,
            unit="percent",
            labels=labels or {}
        )
        
        self.dashboard_logger.info(
            "PERFORMANCE_METRIC",
            extra={
                "metric_data": metric.to_dict(),
                "dashboard_type": "cache_hit_rate",
                "service": self.service_name
            }
        )
    
    def log_performance_breakdown(
        self,
        operation: str,
        total_duration_ms: float,
        stages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Log detailed performance breakdown for complex operations.
        
        Args:
            operation: Operation name
            total_duration_ms: Total operation duration
            stages: List of stage breakdowns with timing
            metadata: Additional metadata
            trace_id: Request trace ID
            request_id: Request ID
        """
        breakdown = PerformanceBreakdown(
            timestamp=datetime.now(timezone.utc).isoformat(),
            operation=operation,
            total_duration_ms=total_duration_ms,
            stages=stages,
            metadata=metadata or {},
            trace_id=trace_id,
            request_id=request_id
        )
        
        self.dashboard_logger.info(
            "PERFORMANCE_BREAKDOWN",
            extra={
                "breakdown_data": breakdown.to_dict(),
                "dashboard_type": "breakdown",
                "service": self.service_name
            }
        )
    
    def log_resource_usage_metric(
        self,
        component_type: ComponentType,
        component_name: str,
        resource_type: str,  # cpu, memory, connections, etc.
        usage_value: float,
        unit: str,
        labels: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log resource usage metric for dashboard consumption.
        
        Args:
            component_type: Type of component
            component_name: Specific component name
            resource_type: Type of resource (cpu, memory, connections)
            usage_value: Resource usage value
            unit: Unit of measurement
            labels: Additional labels for filtering/grouping
        """
        metric = PerformanceMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.RESOURCE_USAGE.value,
            component_type=component_type.value,
            component_name=component_name,
            operation=resource_type,
            value=usage_value,
            unit=unit,
            labels=labels or {}
        )
        
        self.dashboard_logger.info(
            "PERFORMANCE_METRIC",
            extra={
                "metric_data": metric.to_dict(),
                "dashboard_type": "resource_usage",
                "service": self.service_name
            }
        )


# Global dashboard instance
dashboard = PerformanceDashboard()


def log_grpc_latency(
    handler_name: str,
    method: str,
    duration_ms: float,
    success: bool = True,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Convenience function to log gRPC handler latency.
    
    Args:
        handler_name: Name of the gRPC handler
        method: gRPC method name
        duration_ms: Duration in milliseconds
        success: Whether the operation was successful
        trace_id: Request trace ID
        request_id: Request ID
    """
    dashboard.log_latency_metric(
        component_type=ComponentType.GRPC_HANDLER,
        component_name=handler_name,
        operation=method,
        duration_ms=duration_ms,
        labels={"success": success},
        trace_id=trace_id,
        request_id=request_id
    )


def log_cache_latency(
    backend_name: str,
    operation: str,
    duration_ms: float,
    cache_hit: Optional[bool] = None,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Convenience function to log cache operation latency.
    
    Args:
        backend_name: Name of the cache backend
        operation: Cache operation (get, set, delete)
        duration_ms: Duration in milliseconds
        cache_hit: Whether it was a cache hit (for get operations)
        trace_id: Request trace ID
        request_id: Request ID
    """
    labels = {}
    if cache_hit is not None:
        labels["cache_hit"] = cache_hit
    
    dashboard.log_latency_metric(
        component_type=ComponentType.CACHE_BACKEND,
        component_name=backend_name,
        operation=operation,
        duration_ms=duration_ms,
        labels=labels,
        trace_id=trace_id,
        request_id=request_id
    )


def log_external_api_latency(
    service_name: str,
    operation: str,
    duration_ms: float,
    success: bool = True,
    status_code: Optional[int] = None,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Convenience function to log external API call latency.
    
    Args:
        service_name: Name of the external service
        operation: API operation
        duration_ms: Duration in milliseconds
        success: Whether the operation was successful
        status_code: HTTP status code
        trace_id: Request trace ID
        request_id: Request ID
    """
    labels = {"success": success}
    if status_code is not None:
        labels["status_code"] = status_code
    
    dashboard.log_latency_metric(
        component_type=ComponentType.EXTERNAL_API,
        component_name=service_name,
        operation=operation,
        duration_ms=duration_ms,
        labels=labels,
        trace_id=trace_id,
        request_id=request_id
    )