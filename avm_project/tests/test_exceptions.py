"""
Unit tests for custom exception classes
"""

import pytest
from avm_project.exceptions import (
    ModelNotFoundError,
    InvalidInputError,
    PredictionError,
    DataValidationError,
    ConfigurationError,
    PathError,
    DatabaseError,
    APIError,
    TimeoutError as AVMTimeoutError,
    UnauthorizedError
)


class TestModelNotFoundError:
    """Test ModelNotFoundError exception"""

    def test_raise_model_not_found(self):
        """Test raising ModelNotFoundError"""
        with pytest.raises(ModelNotFoundError) as exc_info:
            raise ModelNotFoundError("RandomForest model not found")
        assert "RandomForest model not found" in str(exc_info.value)

    def test_model_not_found_with_model_name(self):
        """Test error message with model name"""
        model_name = "GradientBoosting"
        with pytest.raises(ModelNotFoundError):
            raise ModelNotFoundError(f"Model {model_name} not found at path")

    def test_exception_inheritance(self):
        """Test that ModelNotFoundError inherits from Exception"""
        assert issubclass(ModelNotFoundError, Exception)


class TestInvalidInputError:
    """Test InvalidInputError exception"""

    def test_raise_invalid_input(self):
        """Test raising InvalidInputError"""
        with pytest.raises(InvalidInputError) as exc_info:
            raise InvalidInputError("area_sqm must be positive")
        assert "area_sqm must be positive" in str(exc_info.value)

    def test_invalid_input_with_field_name(self):
        """Test error message with field name"""
        with pytest.raises(InvalidInputError):
            raise InvalidInputError("Field 'rooms' must be integer between 0-20")

    def test_invalid_input_multiple_fields(self):
        """Test error with multiple invalid fields"""
        errors = ["area_sqm < 0", "year_built > 2030"]
        with pytest.raises(InvalidInputError):
            raise InvalidInputError(f"Invalid fields: {', '.join(errors)}")


class TestPredictionError:
    """Test PredictionError exception"""

    def test_raise_prediction_error(self):
        """Test raising PredictionError"""
        with pytest.raises(PredictionError) as exc_info:
            raise PredictionError("Model prediction failed")
        assert "Model prediction failed" in str(exc_info.value)

    def test_prediction_error_with_context(self):
        """Test prediction error with additional context"""
        with pytest.raises(PredictionError):
            raise PredictionError("Prediction failed for batch_id: 123")

    def test_prediction_error_handling(self):
        """Test catching and re-raising prediction error"""
        try:
            raise PredictionError("Internal model error")
        except PredictionError as e:
            assert "Internal model error" in str(e)


class TestDataValidationError:
    """Test DataValidationError exception"""

    def test_raise_data_validation_error(self):
        """Test raising DataValidationError"""
        with pytest.raises(DataValidationError) as exc_info:
            raise DataValidationError("Data shape mismatch")
        assert "Data shape mismatch" in str(exc_info.value)

    def test_validation_error_missing_features(self):
        """Test validation error for missing features"""
        missing = ["feature1", "feature2"]
        with pytest.raises(DataValidationError):
            raise DataValidationError(f"Missing features: {missing}")

    def test_validation_error_with_count(self):
        """Test validation error with row/column counts"""
        with pytest.raises(DataValidationError):
            raise DataValidationError("Expected 25 columns, got 20")


class TestConfigurationError:
    """Test ConfigurationError exception"""

    def test_raise_configuration_error(self):
        """Test raising ConfigurationError"""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Invalid API configuration")
        assert "Invalid API configuration" in str(exc_info.value)

    def test_configuration_error_missing_key(self):
        """Test error for missing configuration key"""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Missing required env var: API_KEY")

    def test_configuration_error_invalid_value(self):
        """Test error for invalid configuration value"""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")


class TestPathError:
    """Test PathError exception"""

    def test_raise_path_error(self):
        """Test raising PathError"""
        with pytest.raises(PathError) as exc_info:
            raise PathError("Model path does not exist")
        assert "Model path does not exist" in str(exc_info.value)

    def test_path_error_invalid_path(self):
        """Test error for invalid path"""
        with pytest.raises(PathError):
            raise PathError("/invalid/path/to/models")

    def test_path_error_permission_denied(self):
        """Test error for permission denied"""
        with pytest.raises(PathError):
            raise PathError("Permission denied: cannot write to /models")


class TestDatabaseError:
    """Test DatabaseError exception"""

    def test_raise_database_error(self):
        """Test raising DatabaseError"""
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("Database connection failed")
        assert "Database connection failed" in str(exc_info.value)

    def test_database_error_connection(self):
        """Test connection error"""
        with pytest.raises(DatabaseError):
            raise DatabaseError("Unable to connect to PostgreSQL")

    def test_database_error_query(self):
        """Test query execution error"""
        with pytest.raises(DatabaseError):
            raise DatabaseError("Query execution failed: table not found")


class TestAPIError:
    """Test APIError exception"""

    def test_raise_api_error(self):
        """Test raising APIError"""
        with pytest.raises(APIError) as exc_info:
            raise APIError("External API request failed")
        assert "External API request failed" in str(exc_info.value)

    def test_api_error_status_code(self):
        """Test API error with status code"""
        with pytest.raises(APIError):
            raise APIError("API returned 503: Service Unavailable")

    def test_api_error_response(self):
        """Test API error with response content"""
        with pytest.raises(APIError):
            raise APIError("Invalid response format from Data.go.kr API")


class TestAVMTimeoutError:
    """Test TimeoutError exception"""

    def test_raise_timeout_error(self):
        """Test raising TimeoutError"""
        with pytest.raises(AVMTimeoutError) as exc_info:
            raise AVMTimeoutError("Prediction timeout exceeded")
        assert "Prediction timeout exceeded" in str(exc_info.value)

    def test_timeout_error_duration(self):
        """Test timeout error with duration"""
        with pytest.raises(AVMTimeoutError):
            raise AVMTimeoutError("Operation exceeded 30s timeout")

    def test_timeout_error_operation(self):
        """Test timeout error with operation context"""
        with pytest.raises(AVMTimeoutError):
            raise AVMTimeoutError("Model training exceeded 600s limit")


class TestUnauthorizedError:
    """Test UnauthorizedError exception"""

    def test_raise_unauthorized_error(self):
        """Test raising UnauthorizedError"""
        with pytest.raises(UnauthorizedError) as exc_info:
            raise UnauthorizedError("API key invalid")
        assert "API key invalid" in str(exc_info.value)

    def test_unauthorized_error_auth(self):
        """Test unauthorized access error"""
        with pytest.raises(UnauthorizedError):
            raise UnauthorizedError("Authentication failed: invalid credentials")

    def test_unauthorized_error_scope(self):
        """Test authorization scope error"""
        with pytest.raises(UnauthorizedError):
            raise UnauthorizedError("Insufficient permissions for operation")


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships"""

    def test_all_exceptions_inherit_from_exception(self):
        """Test that all custom exceptions inherit from Exception"""
        exceptions = [
            ModelNotFoundError,
            InvalidInputError,
            PredictionError,
            DataValidationError,
            ConfigurationError,
            PathError,
            DatabaseError,
            APIError,
            AVMTimeoutError,
            UnauthorizedError
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, Exception)

    def test_catch_generic_exception(self):
        """Test catching custom exceptions as generic Exception"""
        with pytest.raises(Exception):
            raise ModelNotFoundError("test")

    def test_catch_specific_exception(self):
        """Test catching specific exception does not catch others"""
        with pytest.raises(ModelNotFoundError):
            try:
                raise InvalidInputError("test")
            except ModelNotFoundError:
                pass
            raise ModelNotFoundError("test")


class TestExceptionMessages:
    """Test exception message formatting"""

    def test_exception_message_preserves_content(self):
        """Test that exception message preserves input content"""
        message = "This is a detailed error message"
        exc = InvalidInputError(message)
        assert message in str(exc)

    def test_exception_chaining(self):
        """Test exception chaining with context"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise DataValidationError(f"Validation failed: {e}") from e
        except DataValidationError as e:
            assert e.__cause__ is not None

    def test_multiple_exception_types_in_handler(self):
        """Test handling multiple exception types"""
        errors = []
        for i in range(3):
            try:
                if i == 0:
                    raise ModelNotFoundError("Model not found")
                elif i == 1:
                    raise InvalidInputError("Invalid input")
                else:
                    raise PredictionError("Prediction failed")
            except (ModelNotFoundError, InvalidInputError, PredictionError) as e:
                errors.append(type(e).__name__)

        assert len(errors) == 3
        assert "ModelNotFoundError" in errors
        assert "InvalidInputError" in errors
        assert "PredictionError" in errors
