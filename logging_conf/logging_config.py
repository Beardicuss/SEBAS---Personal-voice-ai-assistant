# -*- coding: utf-8 -*-
"""
Structured Logging Configuration
Phase 1.5: Observability & Audit Framework
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing and aggregation.
    """
    
    def __init__(self, include_timestamp: bool = True, include_level: bool = True,
                 include_module: bool = True, include_thread: bool = True):
        """
        Initialize structured formatter.
        
        Args:
            include_timestamp: Include timestamp in output
            include_level: Include log level in output
            include_module: Include module/logger name in output
            include_thread: Include thread name in output
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_module = include_module
        self.include_thread = include_thread
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            'message': record.getMessage()
        }
        
        if self.include_timestamp:
            log_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
            log_data['timestamp_unix'] = record.created
        
        if self.include_level:
            log_data['level'] = record.levelname
        
        if self.include_module:
            log_data['logger'] = record.name
            log_data['module'] = record.module
            log_data['function'] = record.funcName
            log_data['line'] = record.lineno
        
        if self.include_thread:
            log_data['thread'] = record.threadName
            log_data['thread_id'] = record.thread
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields from record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add context if available (from LogContext)
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class LogContext:
    """
    Context manager for adding contextual information to logs.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize log context.
        
        Args:
            **kwargs: Contextual data to add to logs
        """
        self.context = kwargs
        self.old_context = None
    
    def __enter__(self):
        """Enter context manager."""
        # Store old context
        self.old_context = getattr(logging.currentframe(1), 'log_context', None)
        
        # Set new context
        frame = sys._getframe(1)
        frame.f_locals['log_context'] = self.context
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        # Restore old context
        frame = sys._getframe(1)
        if self.old_context is not None:
            frame.f_locals['log_context'] = self.old_context
        else:
            frame.f_locals.pop('log_context', None)
    
    @staticmethod
    def get_current_context() -> Dict[str, Any]:
        """Get current log context."""
        frame = sys._getframe(1)
        return getattr(frame, 'log_context', {})


class AuditLogger:
    """
    Specialized logger for audit trail events.
    """
    
    def __init__(self, name: str = 'sebas.audit'):
        """
        Initialize audit logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
    
    def log_event(self, event_type: str, user_id: Optional[str] = None,
                  action: Optional[str] = None, resource: Optional[str] = None,
                  result: Optional[str] = None, details: Optional[Dict] = None):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., 'command.executed', 'user.login')
            user_id: User identifier
            action: Action performed
            resource: Resource affected
            result: Result of action ('success', 'failure', etc.)
            details: Additional details
        """
        audit_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }
        
        if user_id:
            audit_data['user_id'] = user_id
        if action:
            audit_data['action'] = action
        if resource:
            audit_data['resource'] = resource
        if result:
            audit_data['result'] = result
        if details:
            audit_data['details'] = details
        
        # Use extra parameter to pass audit data
        self.logger.info(
            f"Audit: {event_type}",
            extra={'audit': audit_data, 'extra_fields': audit_data}
        )


def setup_structured_logging(
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    log_format: str = 'json',
    log_level: str = 'INFO',
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up structured logging for SEBAS.
    
    Args:
        log_file: Log file path (defaults to ~/sebas.log)
        log_dir: Log directory (defaults to user home)
        log_format: 'json' or 'text'
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Enable console output
        file_output: Enable file output
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured root logger
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Env-driven overrides for log retention and console/level
    try:
        env_max_mb = os.environ.get('SEBAS_LOG_MAX_MB')
        if env_max_mb:
            max_bytes = max(1, int(float(env_max_mb))) * 1024 * 1024
        env_backups = os.environ.get('SEBAS_LOG_BACKUPS')
        if env_backups:
            backup_count = max(1, int(env_backups))
        env_level = os.environ.get('SEBAS_LOG_LEVEL')
        if env_level:
            log_level = env_level.upper()
        env_console = os.environ.get('SEBAS_CONSOLE_LOG')
        if env_console is not None:
            console_output = str(env_console).lower() in ('1','true','yes','on')
    except Exception:
        pass

    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    if log_format.lower() == 'json':
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] [%(threadName)s] %(message)s'
        )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)  # Console shows INFO and above
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if file_output:
        if log_file is None:
            if log_dir is None:
                log_dir = os.path.expanduser('~')
            log_file = os.path.join(log_dir, 'sebas.log')
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # File logs everything
        root_logger.addHandler(file_handler)
    
    # Create audit log file
    audit_log_file = os.path.join(os.path.dirname(log_file or os.path.expanduser('~')), 'sebas_audit.log')
    audit_handler = logging.handlers.RotatingFileHandler(
        audit_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    audit_handler.setFormatter(StructuredFormatter())
    audit_handler.setLevel(logging.INFO)
    
    audit_logger = logging.getLogger('sebas.audit')
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # Don't propagate to root logger
    
    return root_logger


def get_audit_logger() -> AuditLogger:
    """Get the audit logger instance."""
    return AuditLogger()


# Convenience function for structured logging
def log_with_context(level: str, message: str, **context):
    """
    Log a message with contextual information.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        **context: Additional context data
    """
    logger = logging.getLogger()
    log_func = getattr(logger, level.lower(), logger.info)
    
    # Create a custom record with context
    extra = {'extra_fields': context}
    log_func(message, extra=extra)
