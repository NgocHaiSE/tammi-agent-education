"""
Performance logging utilities for detailed timing analysis.

This module provides decorators and context managers to track performance
bottlenecks with microsecond precision and structured logging.
"""

import time
import asyncio
import functools
from typing import Dict, Any, Optional, List, Callable, Union
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum

from agent.utils.logging import get_logger, log_with_context
from agent.utils.trace_context import get_current_trace_id, get_current_request_id

logger = get_logger(__name__)


class PerformanceLevel(Enum):
    """Performance logging levels."""
    CRITICAL = "CRITICAL"  # > 1000ms
    WARNING = "WARNING"    # > 500ms
    INFO = "INFO"         # > 100ms
    DEBUG = "DEBUG"       # All operations


@dataclass
class TimingBreakdown:
    """Detailed timing breakdown for operations."""
    operation_name: str
    total_duration_ms: float
    stages: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.perf_counter)
    
    def add_stage(self, stage_name: str, duration_ms: float, **metadata):
        """Add a timing stage with optional metadata."""
        self.stages[stage_name] = duration_ms
        if metadata:
            self.metadata[f"{stage_name}_metadata"] = metadata
    
    def get_percentage_breakdown(self) -> Dict[str, float]:
        """Get percentage breakdown of each stage."""
        if self.total_duration_ms == 0:
            return {}
        return {
            stage: (duration / self.total_duration_ms) * 100
            for stage, duration in self.stages.items()
        }
    
    def get_performance_level(self) -> PerformanceLevel:
        """Determine performance level based on total duration."""
        # Cache and external API operations should always be at least INFO level
        # for visibility into cache hits/misses
        is_cache_or_api = any(x in self.operation_name.lower() 
                             for x in ['cache', 'external_api', 'redis'])
        
        if self.total_duration_ms > 1000:
            return PerformanceLevel.CRITICAL
        elif self.total_duration_ms > 500:
            return PerformanceLevel.WARNING
        elif self.total_duration_ms > 100 or is_cache_or_api:
            return PerformanceLevel.INFO
        else:
            return PerformanceLevel.DEBUG


class PerformanceTimer:
    """High-precision performance timer with stage tracking."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = time.perf_counter()
        self.stages: List[tuple] = []  # (stage_name, start_time, end_time, metadata)
        self.current_stage_start = None
        self.current_stage_name = None
        
    def start_stage(self, stage_name: str, **metadata):
        """Start timing a new stage."""
        now = time.perf_counter()
        
        # End previous stage if exists
        if self.current_stage_start is not None:
            self.stages.append((
                self.current_stage_name,
                self.current_stage_start,
                now,
                {}
            ))
        
        self.current_stage_start = now
        self.current_stage_name = stage_name
        
    def end_stage(self, **metadata):
        """End current stage with optional metadata."""
        if self.current_stage_start is not None:
            now = time.perf_counter()
            self.stages.append((
                self.current_stage_name,
                self.current_stage_start,
                now,
                metadata
            ))
            self.current_stage_start = None
            self.current_stage_name = None
    
    def get_breakdown(self) -> TimingBreakdown:
        """Get detailed timing breakdown."""
        # End current stage if still running
        if self.current_stage_start is not None:
            self.end_stage()
            
        total_duration = (time.perf_counter() - self.start_time) * 1000
        breakdown = TimingBreakdown(
            operation_name=self.operation_name,
            total_duration_ms=total_duration,
            start_time=self.start_time
        )
        
        for stage_name, start_time, end_time, metadata in self.stages:
            stage_duration_ms = (end_time - start_time) * 1000
            breakdown.add_stage(stage_name, stage_duration_ms, **metadata)
            
        return breakdown


@asynccontextmanager
async def async_performance_context(operation_name: str, 
                                  log_threshold_ms: float = 0,
                                  include_system_info: bool = False):
    """
    Async context manager for performance tracking.
    
    Args:
        operation_name: Name of the operation being tracked
        log_threshold_ms: Only log if duration exceeds this threshold
        include_system_info: Include system resource info in logs
    """
    timer = PerformanceTimer(operation_name)
    
    try:
        yield timer
    finally:
        breakdown = timer.get_breakdown()
        
        if breakdown.total_duration_ms >= log_threshold_ms:
            await _log_performance_breakdown(breakdown, include_system_info)


@contextmanager
def performance_context(operation_name: str, 
                       log_threshold_ms: float = 0,
                       include_system_info: bool = False):
    """
    Sync context manager for performance tracking.
    
    Args:
        operation_name: Name of the operation being tracked
        log_threshold_ms: Only log if duration exceeds this threshold
        include_system_info: Include system resource info in logs
    """
    timer = PerformanceTimer(operation_name)
    
    try:
        yield timer
    finally:
        breakdown = timer.get_breakdown()
        
        if breakdown.total_duration_ms >= log_threshold_ms:
            _log_performance_breakdown_sync(breakdown, include_system_info)


def performance_monitor(operation_name: Optional[str] = None,
                       log_threshold_ms: float = 100,
                       include_args: bool = False,
                       include_system_info: bool = False):
    """
    Decorator for automatic performance monitoring.
    
    Args:
        operation_name: Custom operation name (defaults to function name)
        log_threshold_ms: Only log if duration exceeds this threshold
        include_args: Include function arguments in logs
        include_system_info: Include system resource info in logs
    """
    def decorator(func: Callable):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with async_performance_context(
                    op_name, log_threshold_ms, include_system_info
                ) as timer:
                    timer.start_stage("function_execution")
                    
                    if include_args:
                        timer.get_breakdown().metadata["args"] = str(args)[:200]
                        timer.get_breakdown().metadata["kwargs"] = str(kwargs)[:200]
                    
                    try:
                        result = await func(*args, **kwargs)
                        timer.end_stage(success=True)
                        return result
                    except Exception as e:
                        timer.end_stage(success=False, error=str(e)[:200])
                        raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with performance_context(
                    op_name, log_threshold_ms, include_system_info
                ) as timer:
                    timer.start_stage("function_execution")
                    
                    if include_args:
                        timer.get_breakdown().metadata["args"] = str(args)[:200]
                        timer.get_breakdown().metadata["kwargs"] = str(kwargs)[:200]
                    
                    try:
                        result = func(*args, **kwargs)
                        timer.end_stage(success=True)
                        return result
                    except Exception as e:
                        timer.end_stage(success=False, error=str(e)[:200])
                        raise
            return sync_wrapper
    return decorator


async def _log_performance_breakdown(breakdown: TimingBreakdown, 
                                   include_system_info: bool = False):
    """Log performance breakdown asynchronously."""
    _log_performance_breakdown_sync(breakdown, include_system_info)


def _log_performance_breakdown_sync(breakdown: TimingBreakdown, 
                                  include_system_info: bool = False):
    """Log performance breakdown synchronously."""
    perf_level = breakdown.get_performance_level()
    percentages = breakdown.get_percentage_breakdown()
    
    log_data = {
        "operation": breakdown.operation_name,
        "total_duration_ms": round(breakdown.total_duration_ms, 2),
        "performance_level": perf_level.value,
        "stage_breakdown_ms": {k: round(v, 2) for k, v in breakdown.stages.items()},
        "stage_percentages": {k: round(v, 1) for k, v in percentages.items()},
        "trace_id": get_current_trace_id(),
        "request_id": get_current_request_id(),
    }
    
    # Add metadata
    if breakdown.metadata:
        log_data["metadata"] = breakdown.metadata
    
    # Add system info if requested
    if include_system_info:
        try:
            import psutil
            process = psutil.Process()
            log_data["system_info"] = {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                "open_files": len(process.open_files()),
            }
        except ImportError:
            log_data["system_info"] = {"note": "psutil not available"}
    
    # Log at appropriate level
    if perf_level == PerformanceLevel.CRITICAL:
        log_with_context(logger, 40, "PERFORMANCE CRITICAL: Slow operation detected", **log_data)
    elif perf_level == PerformanceLevel.WARNING:
        log_with_context(logger, 30, "PERFORMANCE WARNING: Operation slower than expected", **log_data)
    elif perf_level == PerformanceLevel.INFO:
        log_with_context(logger, 20, "PERFORMANCE INFO: Operation timing breakdown", **log_data)
    else:
        log_with_context(logger, 10, "PERFORMANCE DEBUG: Operation timing breakdown", **log_data)


# Convenience functions for common use cases
async def time_cache_operation(operation_name: str, cache_func: Callable, *args, **kwargs):
    """Time a cache operation with detailed breakdown."""
    async with async_performance_context(f"cache_{operation_name}", log_threshold_ms=10) as timer:
        timer.start_stage("cache_key_generation")
        # Key generation timing would be handled by the cache implementation
        timer.end_stage()
        
        timer.start_stage("cache_operation")
        try:
            result = await cache_func(*args, **kwargs)
            timer.end_stage(success=True, cache_hit=result is not None)
            return result
        except Exception as e:
            timer.end_stage(success=False, error=str(e)[:200])
            raise


async def time_external_api_call(api_name: str, http_func: Callable, *args, **kwargs):
    """Time an external API call with detailed breakdown."""
    async with async_performance_context(f"external_api_{api_name}", log_threshold_ms=50) as timer:
        timer.start_stage("request_preparation")
        # Request prep timing would be handled by the HTTP client
        timer.end_stage()
        
        timer.start_stage("network_call")
        try:
            result = await http_func(*args, **kwargs)
            timer.end_stage(success=True, status_code=getattr(result, 'status_code', None))
            return result
        except Exception as e:
            timer.end_stage(success=False, error=str(e)[:200])
            raise


def time_serialization(operation_name: str, serialize_func: Callable, data: Any):
    """Time serialization operations."""
    with performance_context(f"serialization_{operation_name}", log_threshold_ms=5) as timer:
        timer.start_stage("data_serialization")
        try:
            result = serialize_func(data)
            data_size = len(str(result)) if result else 0
            timer.end_stage(success=True, data_size_bytes=data_size)
            return result
        except Exception as e:
            timer.end_stage(success=False, error=str(e)[:200])
            raise