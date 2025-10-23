"""Data validation service for Driver Insight Agent."""

from typing import Any, Dict, List, Optional, Tuple

from ..config import get_config
from .logger import get_logger


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, errors: List[str]):
        """Initialize validation error.
        
        Args:
            message: Error message
            errors: List of specific validation errors
        """
        super().__init__(message)
        self.errors = errors


class DriverDataValidator:
    """Validator for driver data."""
    
    def __init__(self):
        """Initialize the validator."""
        self.logger = get_logger()
    
    def validate_driver_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate driver data against required fields.
        
        Args:
            data: Driver data dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            config = get_config()
            required_fields = config.validation.required_fields
        except RuntimeError:
            # Fallback if config not loaded
            required_fields = ["driver_id", "name"]
        
        errors = []
        
        # Check if data is a dictionary
        if not isinstance(data, dict):
            errors.append("Data must be a dictionary")
            self.logger.log_validation_result("driver_data", False, errors, data_type=type(data).__name__)
            return False, errors
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif data[field] is None:
                errors.append(f"Required field cannot be null: {field}")
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f"Required field cannot be empty: {field}")
        
        # Validate specific field types and formats
        validation_errors = self._validate_field_types(data)
        errors.extend(validation_errors)
        
        is_valid = len(errors) == 0
        self.logger.log_validation_result("driver_data", is_valid, errors if not is_valid else None)
        
        return is_valid, errors
    
    def _validate_field_types(self, data: Dict[str, Any]) -> List[str]:
        """Validate specific field types and formats.
        
        Args:
            data: Driver data dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate driver_id format
        if "driver_id" in data and data["driver_id"] is not None:
            driver_id = data["driver_id"]
            if not isinstance(driver_id, str):
                errors.append("driver_id must be a string")
            elif len(driver_id.strip()) == 0:
                errors.append("driver_id cannot be empty")
        
        # Validate name format
        if "name" in data and data["name"] is not None:
            name = data["name"]
            if not isinstance(name, str):
                errors.append("name must be a string")
            elif len(name.strip()) == 0:
                errors.append("name cannot be empty")
        
        # Validate rating if present
        if "rating" in data and data["rating"] is not None:
            rating = data["rating"]
            if not isinstance(rating, (int, float)):
                errors.append("rating must be a number")
            elif rating < 0 or rating > 5:
                errors.append("rating must be between 0 and 5")
        
        # Validate vehicle if present
        if "vehicle" in data and data["vehicle"] is not None:
            vehicle = data["vehicle"]
            if not isinstance(vehicle, str):
                errors.append("vehicle must be a string")
        
        # Validate status if present
        if "status" in data and data["status"] is not None:
            status = data["status"]
            if not isinstance(status, str):
                errors.append("status must be a string")
            elif status.lower() not in ["active", "inactive", "suspended", "pending"]:
                errors.append("status must be one of: active, inactive, suspended, pending")
        
        return errors
    
    def validate_driver_batch(self, data_list: List[Dict[str, Any]]) -> Tuple[bool, Dict[int, List[str]]]:
        """Validate a batch of driver data.
        
        Args:
            data_list: List of driver data dictionaries
            
        Returns:
            Tuple of (all_valid, dict_of_errors_by_index)
        """
        if not isinstance(data_list, list):
            error_msg = "Batch data must be a list"
            self.logger.log_validation_result("driver_batch", False, [error_msg])
            return False, {0: [error_msg]}
        
        all_valid = True
        errors_by_index = {}
        
        for index, driver_data in enumerate(data_list):
            is_valid, errors = self.validate_driver_data(driver_data)
            if not is_valid:
                all_valid = False
                errors_by_index[index] = errors
        
        self.logger.log_validation_result(
            "driver_batch", 
            all_valid, 
            None if all_valid else list(errors_by_index.keys()),
            total_items=len(data_list),
            invalid_items=len(errors_by_index)
        )
        
        return all_valid, errors_by_index
    
    def validate_driver_ids(self, driver_ids: List[str]) -> Tuple[bool, List[str]]:
        """Validate a list of driver IDs.
        
        Args:
            driver_ids: List of driver ID strings
            
        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []
        
        if not isinstance(driver_ids, list):
            errors.append("Driver IDs must be provided as a list")
            return False, errors
        
        if len(driver_ids) == 0:
            errors.append("Driver IDs list cannot be empty")
            return False, errors
        
        for i, driver_id in enumerate(driver_ids):
            if not isinstance(driver_id, str):
                errors.append(f"Driver ID at index {i} must be a string")
            elif not driver_id.strip():
                errors.append(f"Driver ID at index {i} cannot be empty")
        
        is_valid = len(errors) == 0
        self.logger.log_validation_result("driver_ids", is_valid, errors if not is_valid else None)
        
        return is_valid, errors
    
    def sanitize_driver_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize driver data by removing invalid fields and normalizing values.
        
        Args:
            data: Raw driver data
            
        Returns:
            Sanitized driver data
        """
        if not isinstance(data, dict):
            return {}
        
        sanitized = {}
        
        # Get allowed fields from config
        try:
            config = get_config()
            allowed_fields = config.validation.required_fields + config.validation.optional_fields
        except RuntimeError:
            allowed_fields = ["driver_id", "name", "vehicle", "rating", "status", "location"]
        
        for field, value in data.items():
            if field in allowed_fields and value is not None:
                # Normalize string values
                if isinstance(value, str):
                    sanitized[field] = value.strip()
                # Normalize rating
                elif field == "rating" and isinstance(value, (int, float)):
                    sanitized[field] = max(0, min(5, float(value)))
                # Normalize status
                elif field == "status" and isinstance(value, str):
                    sanitized[field] = value.lower().strip()
                else:
                    sanitized[field] = value
        
        return sanitized


# Global validator instance
_validator: Optional[DriverDataValidator] = None


def get_validator() -> DriverDataValidator:
    """Get the global validator instance.
    
    Returns:
        DriverDataValidator: The validator instance
    """
    global _validator
    if _validator is None:
        _validator = DriverDataValidator()
    return _validator