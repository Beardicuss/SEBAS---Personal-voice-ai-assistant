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
from sebas.datetime import datetime
from sebas.typing import Any, Dict, Optional
from sebas.enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_module: bool = True,
        include_thread: bool = True,
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_module = include_module
        self.include_thread = include_thread

    def format(self, record: logging.LogRecord) -> str:
        """Format record into structured JSON."""
        log_data: Dict[str, Any] = {"message": record.getMessage()}

        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
            log_data["timestamp_unix"] = record.created

        if self.include_level:
            log_data["level"] = record.levelname

        if self.include_module:
            log_data["logger"] = record.name
            log_data["module"] = record.module
            log_data["function"] = record.funcName
            log_data["line"] = record.lineno

        if self.include_thread:
            log_data["thread"] = record.threadName
            log_data["thread_id"] = record.thread

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Safe handling of dynamic fields
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            log_data.update(extra_fields)  # type: ignore[arg-type, assignment]

        context = getattr(record, "context", None)
        if isinstance(context, dict):
            log_data["context"] = context

        return json.dumps(log_data, ensure_ascii=False, default=str)


class LogContext:
    """Context manager for attaching contextual data to logs."""

    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_context = None

    def __enter__(self):
        frame = sys._getframe(1)
        self.old_context = frame.f_locals.get("log_context")
        frame.f_locals["log_context"] = self.context
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        frame = sys._getframe(1)
        if self.old_context is not None:
            frame.f_locals["log_context"] = self.old_context
        else:
            frame.f_locals.pop("log_context", None)

    @staticmethod
    def get_current_context() -> Dict[str, Any]:
        frame = sys._getframe(1)
        return getattr(frame, "log_context", {})


class AuditLogger:
    """Dedicated logger for audit events."""

    def __init__(self, name: str = "sebas.audit"):
        self.logger = logging.getLogger(name)

    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        result: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        audit_data: Dict[str, Any] = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if user_id:
            audit_data["user_id"] = user_id
        if action:
            audit_data["action"] = action
        if resource:
            audit_data["resource"] = resource
        if result:
            audit_data["result"] = result
        if details is not None:
            audit_data["details"] = details

        self.logger.info(
            f"Audit: {event_type}",
            extra={"audit": audit_data, "extra_fields": audit_data},  # type: ignore[arg-type]
        )


def setup_structured_logging(
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    log_format: str = "json",
    log_level: str = "INFO",
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Initialize structured logging for SEBAS."""
    root_logger = logging.getLogger()

    # Handle env overrides gracefully
    try:
        env_max_mb = os.environ.get("SEBAS_LOG_MAX_MB")
        if env_max_mb:
            max_bytes = max(1, int(float(env_max_mb))) * 1024 * 1024
        env_backups = os.environ.get("SEBAS_LOG_BACKUPS")
        if env_backups:
            backup_count = max(1, int(env_backups))
        env_level = os.environ.get("SEBAS_LOG_LEVEL")
        if env_level:
            log_level = env_level.upper()
        env_console = os.environ.get("SEBAS_CONSOLE_LOG")
        if env_console is not None:
            console_output = str(env_console).lower() in ("1", "true", "yes", "on")
    except Exception:
        pass

    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.handlers.clear()

    formatter = (
        StructuredFormatter()
        if log_format.lower() == "json"
        else logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] [%(threadName)s] %(message)s"
        )
    )

    # Console logging
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    # File logging
    if file_output:
        if not log_file:
            log_dir = log_dir or os.path.expanduser("~")
            log_file = os.path.join(log_dir, "sebas.log")

        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

    # Audit log
    audit_log_file = os.path.join(
        os.path.dirname(log_file or os.path.expanduser("~")), "sebas_audit.log"
    )
    audit_handler = logging.handlers.RotatingFileHandler(
        audit_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    audit_handler.setFormatter(StructuredFormatter())
    audit_handler.setLevel(logging.INFO)

    audit_logger = logging.getLogger("sebas.audit")
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    return root_logger


def get_audit_logger() -> AuditLogger:
    return AuditLogger()


def log_with_context(level: str, message: str, **context):
    """Helper for context-aware structured logging."""
    logger = logging.getLogger()
    log_func = getattr(logger, level.lower(), logger.info)
    extra: Dict[str, Any] = {"extra_fields": context}
    log_func(message, extra=extra)  # type: ignore[arg-type]