"""
Validator for driver data fields.
Ensures required fields are present and optionally validates data types.
"""

from typing import Any, Dict, List, Optional

from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, missing_fields: Optional[List[str]] = None):
        """
        Initialize validation error.

        Args:
            message: Error message.
            missing_fields: List of missing field names.
        """
        super().__init__(message)
        self.missing_fields = missing_fields or []


class Validator:
    """
    Validator for driver data.
    Checks for required fields and optionally performs strict validation.
    """

    def __init__(self, required_fields: Optional[List[str]] = None, strict_mode: bool = False):
        """
        Initialize validator.

        Args:
            required_fields: List of required field names. Uses config default if None.
            strict_mode: If True, raises exceptions on validation failure.
        """
        config = get_config()
        self.required_fields = required_fields or config.validation.required_fields
        self.strict_mode = strict_mode if strict_mode is not None else config.validation.strict_mode

        logger.info("Validator initialized", extra={
            "required_fields": self.required_fields,
            "strict_mode": self.strict_mode,
        })

    def validate_driver(self, driver_data: Dict[str, Any]) -> bool:
        """
        Validate a single driver record.

        Args:
            driver_data: Driver data dictionary.

        Returns:
            True if valid, False otherwise (or raises ValidationError in strict mode).

        Raises:
            ValidationError: If validation fails and strict_mode is True.
        """
        missing_fields = self._check_required_fields(driver_data)

        if missing_fields:
            error_msg = f"Validation failed: missing required fields {missing_fields}"
            logger.warning(error_msg, extra={
                "driver_data": driver_data,
                "missing_fields": missing_fields,
            })

            if self.strict_mode:
                raise ValidationError(error_msg, missing_fields=missing_fields)

            return False

        logger.debug("Driver validation passed", extra={
            "driver_id": driver_data.get("driver_id"),
        })
        return True

    def validate_drivers(self, drivers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a list of driver records.

        Args:
            drivers: List of driver data dictionaries.

        Returns:
            Dictionary containing validation results with valid and invalid records.
        """
        valid_drivers = []
        invalid_drivers = []

        for driver in drivers:
            try:
                if self.validate_driver(driver):
                    valid_drivers.append(driver)
                else:
                    invalid_drivers.append({
                        "data": driver,
                        "reason": "Missing required fields",
                        "missing_fields": self._check_required_fields(driver),
                    })
            except ValidationError as e:
                invalid_drivers.append({
                    "data": driver,
                    "reason": str(e),
                    "missing_fields": e.missing_fields,
                })

        result = {
            "total": len(drivers),
            "valid_count": len(valid_drivers),
            "invalid_count": len(invalid_drivers),
            "valid_drivers": valid_drivers,
            "invalid_drivers": invalid_drivers,
        }

        logger.info("Batch validation completed", extra={
            "total": result["total"],
            "valid": result["valid_count"],
            "invalid": result["invalid_count"],
        })

        return result

    def _check_required_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        Check for missing required fields.

        Args:
            data: Data dictionary to check.

        Returns:
            List of missing field names.
        """
        missing = []
        for field in self.required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing.append(field)
        return missing

    def is_valid(self, driver_data: Dict[str, Any]) -> bool:
        """
        Check if driver data is valid without raising exceptions.

        Args:
            driver_data: Driver data dictionary.

        Returns:
            True if valid, False otherwise.
        """
        original_strict = self.strict_mode
        self.strict_mode = False
        result = self.validate_driver(driver_data)
        self.strict_mode = original_strict
        return result
