"""Custom exceptions"""


class AVMException(Exception):
    """Base exception for all AVM project errors"""
    pass


class ModelNotFoundError(AVMException):
    pass


class InvalidInputError(AVMException):
    pass


class PredictionError(AVMException):
    pass


class DataProcessingError(AVMException):
    pass


class APIKeyError(AVMException):
    pass


class CleansingError(DataProcessingError):
    pass


class DataValidationError(DataProcessingError):
    pass


class DataDownloadError(AVMException):
    pass


class IndexingError(DataProcessingError):
    pass


class MigrationError(AVMException):
    pass
