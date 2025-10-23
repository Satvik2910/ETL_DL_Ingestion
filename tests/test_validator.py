"""
Tests for the Validator module.
"""

import pytest

from services.validator import ValidationError, Validator


class TestValidator:
    """Test suite for Validator."""

    def test_validator_initialization(self):
        """Test validator initializes with default config."""
        validator = Validator()
        assert validator is not None
        assert "driver_id" in validator.required_fields
        assert "name" in validator.required_fields

    def test_validator_custom_fields(self):
        """Test validator with custom required fields."""
        validator = Validator(required_fields=["id", "email"])
        assert validator.required_fields == ["id", "email"]

    def test_validate_driver_success(self):
        """Test successful driver validation."""
        validator = Validator(required_fields=["driver_id", "name"])
        driver_data = {
            "driver_id": "D12345",
            "name": "John Doe",
            "vehicle": "Tesla Model Y",
        }
        assert validator.validate_driver(driver_data) is True

    def test_validate_driver_missing_fields(self):
        """Test driver validation with missing fields."""
        validator = Validator(required_fields=["driver_id", "name"], strict_mode=False)
        driver_data = {
            "driver_id": "D12345",
            # Missing 'name'
        }
        assert validator.validate_driver(driver_data) is False

    def test_validate_driver_strict_mode(self):
        """Test strict mode raises exception."""
        validator = Validator(required_fields=["driver_id", "name"], strict_mode=True)
        driver_data = {
            "driver_id": "D12345",
        }
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_driver(driver_data)
        assert "name" in exc_info.value.missing_fields

    def test_validate_drivers_batch(self):
        """Test batch driver validation."""
        validator = Validator(required_fields=["driver_id", "name"])
        drivers = [
            {"driver_id": "D1", "name": "Driver 1"},
            {"driver_id": "D2"},  # Missing name
            {"driver_id": "D3", "name": "Driver 3"},
        ]
        result = validator.validate_drivers(drivers)
        assert result["total"] == 3
        assert result["valid_count"] == 2
        assert result["invalid_count"] == 1

    def test_check_required_fields(self):
        """Test internal field checking."""
        validator = Validator(required_fields=["driver_id", "name", "email"])
        data = {"driver_id": "D1", "name": "John"}
        missing = validator._check_required_fields(data)
        assert "email" in missing
        assert "driver_id" not in missing

    def test_is_valid_method(self):
        """Test is_valid helper method."""
        validator = Validator(required_fields=["driver_id", "name"], strict_mode=True)
        valid_data = {"driver_id": "D1", "name": "John"}
        invalid_data = {"driver_id": "D1"}
        
        assert validator.is_valid(valid_data) is True
        assert validator.is_valid(invalid_data) is False
