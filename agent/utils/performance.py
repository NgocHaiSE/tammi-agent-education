"""
Performance Monitoring and Tracing Utilities

Provides context managers and decorators for tracking execution time,
identifying bottlenecks, and analyzing request latency.

Usage:
    # Method 1: Context manager for code blocks
    with trace_span("database_query", user_id=user_id):
        result = db.query()
    
    # Method 2: Decorator for functions
    @trace_function
    def process_data(data):
        return heavy_computation(data)
    
    # Method 3: Manual timing
    timer = PerformanceTimer("api_call")
    result = api.call()
    timer.stop(status="success", records=len(result))
"""

import time
import asyncio
import functools
import inspect
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
import threading

from agent.utils.logging import get_logger, log_with_context

logger = get_logger(__name__)

# Thread-local storage for nested span tracking
_local = threading.local()


def _get_current_span_stack():
    """Get the current thread's span stack."""
    if not hasattr(_local, 'span_stack'):
        _local.span_stack = []
    return _local.span_stack


def _get_current_depth():
    """Get current nesting depth for spans."""
    return len(_get_current_span_stack())


class PerformanceTimer:
    """
    Timer for measuring execution time with structured logging.
    
    Automatically logs duration when stopped, with support for
    custom metadata and nested timing contexts.
    """
    
    def __init__(
        self,
        operation: str,
        parent_span: Optional[str] = None,
        auto_log: bool = True,
        **metadata
    ):
        """
        Initialize performance timer.
        
        Args:
            operation: Name of the operation being timed
            parent_span: Optional parent span ID for nested operations
            auto_log: Whether to automatically log when stopped
            **metadata: Additional context fields to include in logs
        """
        self.operation = operation
        self.parent_span = parent_span
        self.auto_log = auto_log
        self.metadata = metadata
        
        self.start_time = time.perf_counter()
        self.start_timestamp = datetime.now(timezone.utc)
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.depth = _get_current_depth()
        
        # Add to span stack
        _get_current_span_stack().append(self)
    
    def add_metadata(self, **metadata):
        """
        Add metadata to this performance timer.
        
        Args:
            **metadata: Key-value pairs to add to metadata
        """
        self.metadata.update(metadata)
    
    def stop(self, **extra_metadata) -> float:
        """
        Stop timer and return duration in milliseconds.
        
        Args:
            **extra_metadata: Additional fields to merge with initial metadata
            
        Returns:
            Duration in milliseconds
        """
        if self.end_time is not None:
            return self.duration_ms
        
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        
        # Remove from span stack
        stack = _get_current_span_stack()
        if stack and stack[-1] is self:
            stack.pop()
        
        if self.auto_log:
            # Merge metadata
            log_metadata = {**self.metadata, **extra_metadata}
            self._log_performance(log_metadata)
        
        return self.duration_ms
    
    def _log_performance(self, metadata: Dict[str, Any]):
        """Log performance metrics with structured format."""
        # Determine log level based on duration
        level = self._get_log_level()
        
        # Build log message
        indent = "  " * self.depth
        message = f"{indent}⏱️  {self.operation} completed in {self.duration_ms:.2f}ms"
        
        # Prepare log context
        log_context = {
            "operation": self.operation,
            "duration_ms": round(self.duration_ms, 2),
            "start_time": self.start_timestamp.isoformat(),
            "depth": self.depth,
            **metadata
        }
        
        if self.parent_span:
            log_context["parent_span"] = self.parent_span
        
        # Log with appropriate level
        log_with_context(logger, level, message, **log_context)
    
    def _get_log_level(self) -> int:
        """Determine log level based on duration (for alerting on slow operations)."""
        import logging
        
        # Configurable thresholds (could be moved to settings)
        if self.duration_ms > 5000:  # > 5 seconds
            return logging.WARNING
        elif self.duration_ms > 2000:  # > 2 seconds
            return logging.INFO
        else:
            return logging.DEBUG
    
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer on context exit."""
        if exc_type is not None:
            self.stop(error=str(exc_val), error_type=exc_type.__name__)
        else:
            self.stop()
        return False


@contextmanager
def trace_span(operation: str, **metadata):
    """
    Context manager for tracing a code span with timing.
    
    Example:
        with trace_span("fetch_user_data", user_id=123):
            user = db.get_user(123)
            
    Args:
        operation: Name of the operation
        **metadata: Additional context to log
    """
    timer = PerformanceTimer(operation, **metadata)
    try:
        yield timer
    finally:
        if timer.end_time is None:
            timer.stop()


def trace_function(func: Optional[Callable] = None, *, operation_name: Optional[str] = None):
    """
    Decorator for automatically tracing function execution time.
    
    Example:
        @trace_function
        def process_data(data):
            return heavy_computation(data)
            
        @trace_function(operation_name="custom_name")
        def another_func():
            pass
    
    Args:
        func: Function to wrap (when used without arguments)
        operation_name: Custom operation name (defaults to function name)
    """
    def decorator(f: Callable) -> Callable:
        op_name = operation_name or f.__name__
        
        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            with trace_span(op_name, function=f.__name__, module=f.__module__):
                return f(*args, **kwargs)
        
        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            with trace_span(op_name, function=f.__name__, module=f.__module__):
                return await f(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(f):
            return async_wrapper
        else:
            return sync_wrapper
    
    # Handle both @trace_function and @trace_function()
    if func is None:
        return decorator
    else:
        return decorator(func)


class RequestTracer:
    """
    High-level request tracer for tracking entire request lifecycle.
    
    Tracks:
    - Overall request duration
    - Individual step durations
    - Request metadata (session_id, request_id, etc.)
    - Nested operations
    
    Example:
        tracer = RequestTracer("education_request", session_id=session_id)
        
        with tracer.step("parse_request"):
            parsed = parse(request)
        
        with tracer.step("call_llm"):
            response = llm.invoke(parsed)
        
        tracer.finalize(status="success")
    """
    
    def __init__(self, request_type: str, **metadata):
        """
        Initialize request tracer.
        
        Args:
            request_type: Type of request (e.g., "education", "weather")
            **metadata: Request metadata (session_id, request_id, user_id, etc.)
        """
        self.request_type = request_type
        self.metadata = metadata
        self.start_time = time.perf_counter()
        self.start_timestamp = datetime.now(timezone.utc)
        self.steps: list[Dict[str, Any]] = []
        self.total_duration_ms: Optional[float] = None
        
        # Log request start
        log_with_context(
            logger,
            20,  # INFO
            f"🚀 Starting {request_type}",
            request_type=request_type,
            **metadata
        )
    
    def add_metadata(self, **metadata):
        """
        Add metadata to the request tracer.
        
        This metadata will be included in the final log when finalize() is called.
        
        Args:
            **metadata: Key-value pairs to add to request metadata
        """
        self.metadata.update(metadata)
    
    @contextmanager
    def step(self, step_name: str, **step_metadata):
        """
        Context manager for tracking a request processing step.
        
        Args:
            step_name: Name of the step
            **step_metadata: Additional metadata for this step
        """
        with trace_span(f"{self.request_type}.{step_name}", **step_metadata) as timer:
            yield timer
        
        # Record step info
        self.steps.append({
            "step": step_name,
            "duration_ms": timer.duration_ms,
            **step_metadata
        })
    
    def finalize(self, status: str = "success", **final_metadata):
        """
        Finalize request tracing and log summary.
        
        Args:
            status: Final status (success, error, timeout, etc.)
            **final_metadata: Additional metadata for final log
        """
        end_time = time.perf_counter()
        self.total_duration_ms = (end_time - self.start_time) * 1000
        
        # Calculate step breakdown
        step_summary = {step["step"]: step["duration_ms"] for step in self.steps}
        total_steps_ms = sum(step_summary.values())
        overhead_ms = self.total_duration_ms - total_steps_ms
        
        # Determine log level based on status and duration
        level = 20  # INFO
        if status != "success":
            level = 40  # ERROR
        elif self.total_duration_ms > 5000:
            level = 30  # WARNING
        
        # Log request completion
        log_with_context(
            logger,
            level,
            f"✅ {self.request_type} completed in {self.total_duration_ms:.2f}ms",
            request_type=self.request_type,
            status=status,
            total_duration_ms=round(self.total_duration_ms, 2),
            steps=len(self.steps),
            step_breakdown=step_summary,
            overhead_ms=round(overhead_ms, 2),
            **self.metadata,
            **final_metadata
        )


def log_slow_operation(threshold_ms: float):
    """
    Decorator that only logs if operation exceeds threshold.
    
    Example:
        @log_slow_operation(threshold_ms=100)
        def database_query():
            return db.query()
    
    Args:
        threshold_ms: Minimum duration in ms to trigger logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            
            if duration_ms > threshold_ms:
                log_with_context(
                    logger,
                    30,  # WARNING
                    f"⚠️  Slow operation detected: {func.__name__} took {duration_ms:.2f}ms",
                    function=func.__name__,
                    duration_ms=round(duration_ms, 2),
                    threshold_ms=threshold_ms,
                    exceeded_by_ms=round(duration_ms - threshold_ms, 2)
                )
            
            return result
        return wrapper
    return decorator
