import datetime
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AlphaMind.Exceptions")
logger.setLevel(logging.INFO)


class ErrorSeverity(Enum):
    """Severity levels for errors, mapped to standard logging levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors, used to classify the origin of the failure."""

    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    CONNECTION = "connection"
    EXECUTION = "execution"
    DATA = "data"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class AlphaMindException(Exception):
    """
    Base exception class for all AlphaMind exceptions.
    It automatically logs the error and provides a standardized dictionary representation.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize AlphaMindException.

        Args:
            message: Human-readable error message
            error_code: Unique, machine-readable error code
            category: Error category (e.g., CONFIGURATION, CONNECTION)
            severity: Error severity (e.g., CRITICAL, WARNING)
            details: Additional context for debugging (e.g., failed key, API status)
        """
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.datetime.now()
        log_message = f"[{self.category.value.upper()}] {self.error_code}: {message}"
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={"details": self.details})
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_message, extra={"details": self.details})
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_message, extra={"details": self.details})
        else:
            logger.info(log_message, extra={"details": self.details})
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation for logging/API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class ValidationException(AlphaMindException):
    """Exception raised when input data or parameters are invalid."""

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        field: Optional[str] = None,
    ) -> None:
        """Initialize ValidationException."""
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            details=details,
        )


class ConfigurationException(AlphaMindException):
    """Exception raised for missing or invalid configuration settings."""

    def __init__(
        self,
        message: str,
        error_code: str = "CONFIG_ERROR",
        details: Optional[Dict[str, Any]] = None,
        config_key: Optional[str] = None,
    ) -> None:
        """Initialize ConfigurationException."""
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.ERROR,
            details=details,
        )


class ConnectionException(AlphaMindException):
    """Exception raised for failures connecting to external services (APIs, databases)."""

    def __init__(
        self,
        message: str,
        error_code: str = "CONNECTION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        service: Optional[str] = None,
    ) -> None:
        """Initialize ConnectionException."""
        details = details or {}
        if service:
            details["service"] = service
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.CONNECTION,
            severity=ErrorSeverity.ERROR,
            details=details,
        )


class ExecutionException(AlphaMindException):
    """Exception raised when a module's core operation fails (e.g., model prediction, backtest logic)."""

    def __init__(
        self,
        message: str,
        error_code: str = "EXECUTION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Initialize ExecutionException."""
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.EXECUTION,
            severity=ErrorSeverity.ERROR,
            details=details,
        )


class DataException(AlphaMindException):
    """Exception raised for issues related to data quality, format, or availability."""

    def __init__(
        self,
        message: str,
        error_code: str = "DATA_ERROR",
        details: Optional[Dict[str, Any]] = None,
        data_source: Optional[str] = None,
    ) -> None:
        """Initialize DataException."""
        details = details or {}
        if data_source:
            details["data_source"] = data_source
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.ERROR,
            details=details,
        )


class SystemException(AlphaMindException):
    """Exception raised for underlying system issues (OS, resource limits, unhandled Python errors)."""

    def __init__(
        self,
        message: str,
        error_code: str = "SYSTEM_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize SystemException."""
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            details=details,
        )


def handle_exception(
    exc: Exception,
    default_message: str = "An unexpected error occurred",
    log_traceback: bool = True,
) -> Dict[str, Any]:
    """
    Handle an exception (whether AlphaMind-specific or built-in) and return a
    standardized error response dictionary.

    Args:
        exc: Exception to handle
        default_message: Default message if exception is not an AlphaMindException
        log_traceback: Whether to log the full Python traceback
    """
    if log_traceback:
        logger.error(
            f"Unwrapped exception caught: {exc.__class__.__name__}", exc_info=True
        )
    if isinstance(exc, AlphaMindException):
        return exc.to_dict()
    else:
        system_exc = SystemException(
            message=str(exc) or default_message,
            error_code="UNHANDLED_EXCEPTION",
            details={"exception_type": exc.__class__.__name__},
        )
        return system_exc.to_dict()


class ErrorCollector:
    """Collects and aggregates errors, useful for batch processing or validation steps."""

    def __init__(self) -> None:
        """Initialize error collector."""
        self.errors: List[Dict[str, Any]] = []

    def add_error(self, error: AlphaMindException) -> None:
        """Add an error to the collector (in its dictionary form)."""
        self.errors.append(error.to_dict())

    def add_validation_error(self, message: str, field: Optional[str] = None) -> None:
        """Convenience method to add a ValidationException."""
        error = ValidationException(message=message, field=field)
        self.add_error(error)

    def has_errors(self) -> bool:
        """Check if the collector has any errors."""
        return len(self.errors) > 0

    def has_critical_errors(self) -> bool:
        """Check if the collector has any critical errors."""
        return any((e["severity"] == ErrorSeverity.CRITICAL.value for e in self.errors))

    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all collected errors."""
        return self.errors.copy()

    def clear(self) -> None:
        """Clear all collected errors."""
        self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert collector to dictionary representation for easy review."""
        return {
            "has_errors": self.has_errors(),
            "has_critical_errors": self.has_critical_errors(),
            "error_count": len(self.errors),
            "errors": self.get_errors(),
        }
