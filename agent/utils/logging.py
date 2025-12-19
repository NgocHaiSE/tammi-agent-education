"""
Simplified Logging Module for Tammi Education Agent

Features:
- Daily log rotation with size limits
- Automatic cleanup of old logs
- JSON structured logging
- Vietnam timezone (UTC+7)
- Request/response tracking
"""

import logging
import json
import os
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict

# Get timezone offset for Vietnam (UTC+7)
VIETNAM_TZ = timezone(timedelta(hours=7))

# Constants from environment
DEFAULT_LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
DEFAULT_MAX_BYTES = int(os.environ.get('LOG_MAX_MB_PER_DAY', '100')) * 1024 * 1024  # 100MB default
DEFAULT_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', '90'))  # 90 days default

# Get project root and logs directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / 'logs'

# Track if logging has been configured
_logging_configured = False


def get_vietnam_now() -> datetime:
    """Get current time in Vietnam timezone (UTC+7)"""
    return datetime.now(VIETNAM_TZ)


def get_vietnam_date_string() -> str:
    """Get current date string in Vietnam timezone (YYYY-MM-DD)"""
    return get_vietnam_now().strftime('%Y-%m-%d')


class JsonFormatter(logging.Formatter):
    """JSON formatter with Vietnam timezone"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Build compact logger with location info: "module:line:function"
        logger_info = record.name
        if hasattr(record, 'lineno') and record.lineno:
            logger_info += f":{record.lineno}"
            if hasattr(record, 'funcName') and record.funcName:
                logger_info += f":{record.funcName}"
        
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=VIETNAM_TZ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": logger_info,
        }

        # Merge extra fields if provided
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)

        # Include exception info if present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter with optional colors"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        """
        Args:
            use_colors: If True, include ANSI color codes (for console).
                       If False, plain text (for files).
        """
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created, tz=VIETNAM_TZ).strftime('%H:%M:%S')
        
        # Build message
        if self.use_colors:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            level_str = f"{color}{record.levelname:8s}{reset}"
        else:
            level_str = f"{record.levelname:8s}"
        
        logger_name = record.name.split('.')[-1][:20]  # Last part, max 20 chars
        
        # Get extra fields if available
        extra = getattr(record, "extra_fields", None)
        extra_str = ""
        if isinstance(extra, dict) and extra:
            # Format key fields for console
            key_fields = []
            for key in ['session_id', 'request_id', 'intent', 'duration_ms', 'status']:
                if key in extra:
                    key_fields.append(f"{key}={extra[key]}")
            if key_fields:
                extra_str = f" [{', '.join(key_fields)}]"
        
        msg = f"{timestamp} {level_str} {logger_name:20s} | {record.getMessage()}{extra_str}"
        
        # Include exception if present
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        
        return msg


class DailyRotatingHandler(logging.Handler):
    """
    Custom handler that rotates logs daily and by size.
    
    Main file: education_agent.log
    Backups: YYYY-MM-DD.1.log, YYYY-MM-DD.2.log, etc.
    """
    
    def __init__(self, log_dir, encoding='utf-8', max_bytes=DEFAULT_MAX_BYTES, 
                 retention_days=DEFAULT_RETENTION_DAYS):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.encoding = encoding
        self.max_bytes = max_bytes
        self.retention_days = retention_days
        self.lock = threading.RLock()
        
        # Ensure log directory exists
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # Main log file path
        self.main_log_path = self.log_dir / "education_agent.log"
        
        # Track the last rollover date
        self.last_rollover_date = get_vietnam_date_string()
        
        # Initialize the stream
        self.stream = None
        self._open_stream()
    
    def _open_stream(self):
        """Open the main log file stream"""
        if self.stream:
            self.stream.close()
        
        try:
            self.stream = open(self.main_log_path, 'a', encoding=self.encoding)
        except IOError:
            try:
                self.stream = open(self.main_log_path, 'w', encoding=self.encoding)
            except IOError:
                self.stream = sys.stderr
    
    def _should_rollover(self):
        """Check if rollover should occur"""
        current_date = get_vietnam_date_string()
        
        # Check for day change
        if current_date != self.last_rollover_date:
            return True
        
        # Check for size limit
        try:
            if self.main_log_path.exists() and self.main_log_path.stat().st_size >= self.max_bytes:
                return True
        except (OSError, IOError):
            pass
        
        return False
    
    def _do_rollover(self):
        """Perform the rollover operation"""
        current_date = get_vietnam_date_string()
        
        # Close current stream
        if self.stream and self.stream != sys.stderr:
            self.stream.close()
        
        # Only move the file if it exists and has content
        if self.main_log_path.exists() and self.main_log_path.stat().st_size > 0:
            # Find next available backup number
            backup_num = 1
            while (self.log_dir / f"{current_date}.{backup_num}.log").exists():
                backup_num += 1
            
            # Move main log to backup
            backup_path = self.log_dir / f"{current_date}.{backup_num}.log"
            try:
                self.main_log_path.rename(backup_path)
            except (OSError, IOError):
                pass
        
        # Update the last rollover date
        self.last_rollover_date = current_date
        
        # Open new main log file
        self._open_stream()
        
        # Clean up old files
        self._cleanup_old_logs()
    
    def _cleanup_old_logs(self):
        """Clean up log files older than retention_days"""
        if self.retention_days <= 0:
            return
        
        try:
            cutoff_date = get_vietnam_now() - timedelta(days=self.retention_days)
            
            for log_file in self.log_dir.glob("*.log"):
                # Skip the main log file
                if log_file.name == "education_agent.log":
                    continue
                
                # Check file modification time
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime, tz=VIETNAM_TZ)
                    if mtime < cutoff_date:
                        log_file.unlink()
                except (OSError, IOError):
                    pass
        except Exception:
            pass
    
    def emit(self, record):
        """Emit a log record"""
        try:
            with self.lock:
                # Check if we need to rollover
                if self._should_rollover():
                    self._do_rollover()
                
                # Write the log message
                msg = self.format(record)
                if self.stream:
                    self.stream.write(msg + '\n')
                    self.stream.flush()
        except Exception:
            self.handleError(record)
    
    def close(self):
        """Close the handler"""
        try:
            if self.stream and self.stream != sys.stderr:
                self.stream.close()
        finally:
            self.stream = None
        super().close()


def setup_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    console_output: bool = True,
    file_output: bool = True,
    log_dir: str = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    retention_days: int = DEFAULT_RETENTION_DAYS
):
    """
    Set up logging system with daily rotation and size limits.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        console_output: Whether to output logs to console
        file_output: Whether to output logs to files
        log_dir: Directory to store log files
        max_bytes: Maximum bytes per log file before rollover
        retention_days: Number of days to keep log files
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    # Get log level
    log_level = os.environ.get('LOG_LEVEL', log_level)
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Set default log directory
    if log_dir is None:
        log_dir = os.environ.get('LOG_DIR', str(DEFAULT_LOG_DIR))
    
    # Ensure log directory exists
    Path(log_dir).mkdir(exist_ok=True, parents=True)
    
    # Create formatters
    console_formatter = ConsoleFormatter(use_colors=True)   # Colors for console
    json_formatter = JsonFormatter()                        # JSON for file
    
    # Get root logger
    root = logging.getLogger()
    root.setLevel(numeric_level)
    
    # Remove all handlers before adding new ones
    if root.hasHandlers():
        root.handlers.clear()
    
    # Add console handler with colors
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root.addHandler(console_handler)
    
    # Add file handler with JSON format
    if file_output:
        file_handler = DailyRotatingHandler(
            log_dir=log_dir,
            max_bytes=max_bytes,
            retention_days=retention_days,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(json_formatter)  # JSON format for file
        root.addHandler(file_handler)
    
    # Reduce noise from standard library loggers
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error', 'fastapi', 'httpx', 'httpcore']:
        module_logger = logging.getLogger(logger_name)
        module_logger.setLevel(logging.WARNING)
    
    _logging_configured = True
    
    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized: level={log_level}, console={console_output}, file={file_output}")


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    if not _logging_configured:
        setup_logging()
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, msg: str, **extra_fields: Any) -> None:
    """Log a message with additional context fields"""
    try:
        if hasattr(sys.stdout, 'closed') and sys.stdout.closed:
            return
        if hasattr(sys.stderr, 'closed') and sys.stderr.closed:
            return
        logger.log(level, msg, extra={"extra_fields": extra_fields})
    except (ValueError, OSError, AttributeError):
        pass


# Helper functions for common logging patterns

def log_request(logger: logging.Logger, **fields):
    """Log incoming request with key information"""
    log_with_context(
        logger,
        logging.INFO,
        f"[REQUEST] {fields.get('endpoint', 'unknown')}",
        **fields
    )


def log_response(logger: logging.Logger, duration_ms: float, **fields):
    """Log response with timing information"""
    log_with_context(
        logger,
        logging.INFO,
        f"[RESPONSE] {fields.get('endpoint', 'unknown')} - {duration_ms:.2f}ms",
        duration_ms=duration_ms,
        **fields
    )


def log_llm_call(logger: logging.Logger, model: str, prompt_tokens: int = None, 
                 completion_tokens: int = None, duration_ms: float = None, **fields):
    """Log LLM API call with usage metrics"""
    msg_parts = [f"[LLM] model={model}"]
    if duration_ms:
        msg_parts.append(f"duration={duration_ms:.2f}ms")
    if prompt_tokens:
        msg_parts.append(f"prompt_tokens={prompt_tokens}")
    if completion_tokens:
        msg_parts.append(f"completion_tokens={completion_tokens}")
    
    log_with_context(
        logger,
        logging.INFO,
        " ".join(msg_parts),
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        duration_ms=duration_ms,
        **fields
    )


def log_handler_execution(logger: logging.Logger, handler_type: str, 
                         intent: str = None, sub_intent: str = None,
                         duration_ms: float = None, status: str = "success", **fields):
    """Log handler execution with key metrics"""
    msg = f"[HANDLER] {handler_type}"
    if intent:
        msg += f" intent={intent}"
    if sub_intent:
        msg += f" sub_intent={sub_intent}"
    if duration_ms:
        msg += f" duration={duration_ms:.2f}ms"
    msg += f" status={status}"
    
    log_with_context(
        logger,
        logging.INFO,
        msg,
        handler_type=handler_type,
        intent=intent,
        sub_intent=sub_intent,
        duration_ms=duration_ms,
        status=status,
        **fields
    )


def log_stream_chunk(logger: logging.Logger, chunk_num: int, chunk_size: int, **fields):
    """Log streaming chunk information"""
    log_with_context(
        logger,
        logging.DEBUG,
        f"[STREAM] chunk={chunk_num} size={chunk_size}",
        chunk_num=chunk_num,
        chunk_size=chunk_size,
        **fields
    )

