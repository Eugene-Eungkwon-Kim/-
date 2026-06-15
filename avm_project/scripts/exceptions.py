"""
Custom exception classes for AVM project
Provides specific error types for better error handling and logging
"""


class AVMException(Exception):
    """Base exception for all AVM-related errors"""
    pass


class ModelNotFoundError(AVMException):
    """Raised when a requested model cannot be found"""
    pass


class InvalidInputError(AVMException):
    """Raised when input validation fails"""
    pass


class PredictionError(AVMException):
    """Raised when model prediction fails"""
    pass


class DataProcessingError(AVMException):
    """Raised when data processing/cleaning fails"""
    pass


class DataValidationError(AVMException):
    """Raised when data validation fails"""
    pass


class APIKeyError(AVMException):
    """Raised when API key is missing or invalid"""
    pass


class DataDownloadError(AVMException):
    """Raised when downloading data from APIs fails"""
    pass


class MigrationError(AVMException):
    """Raised when data migration fails"""
    pass


class IndexingError(AVMException):
    """Raised when data indexing fails"""
    pass


class CleansingError(AVMException):
    """Raised when data cleansing fails"""
    pass


class ConfigurationError(AVMException):
    """Raised when configuration is invalid"""
    pass


class ModelTrainingError(AVMException):
    """Raised when model training fails"""
    pass
