"""
Custom exception classes for AVM application
"""


class ModelNotFoundError(Exception):
    """Raised when a requested model is not found"""
    pass


class InvalidInputError(Exception):
    """Raised when input validation fails"""
    pass


class PredictionError(Exception):
    """Raised when model prediction fails"""
    pass


class DataValidationError(Exception):
    """Raised when data validation fails"""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


class PathError(Exception):
    """Raised when path operations fail"""
    pass


class DatabaseError(Exception):
    """Raised when database operations fail"""
    pass


class APIError(Exception):
    """Raised when external API calls fail"""
    pass


class TimeoutError(Exception):
    """Raised when operation exceeds timeout"""
    pass


class UnauthorizedError(Exception):
    """Raised when authorization fails"""
    pass
