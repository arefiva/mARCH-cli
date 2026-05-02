"""
Data validation and sanitization utilities.

Provides DataValidator for schema validation, DataNormalizer for type conversion,
and SanitizationRules for removing sensitive information.
"""

import re
import urllib.parse
from typing import Any, Optional, Union


class DataValidator:
    """
    Validates data against schemas with detailed error reporting.
    """

    def __init__(self) -> None:
        """Initialize DataValidator."""
        self._errors: list[str] = []

    def validate(
        self,
        data: Any,
        schema: dict,
    ) -> tuple[bool, Any, list[str]]:
        """
        Validate data against schema.

        Args:
            data: Data to validate
            schema: Validation schema

        Returns:
            Tuple of (is_valid, normalized_data, error_messages)
        """
        self._errors = []

        if not schema:
            return (True, data, [])

        # Check required fields
        required = schema.get("required", [])
        if isinstance(data, dict):
            for field in required:
                if field not in data:
                    self._errors.append(f"Missing required field: {field}")

        # Check properties
        properties = schema.get("properties", {})
        if isinstance(data, dict):
            for key, value in data.items():
                if key in properties:
                    prop_schema = properties[key]
                    if not self._validate_property(value, prop_schema):
                        self._errors.append(f"Invalid value for property '{key}': {value}")

        return (len(self._errors) == 0, data, self._errors)

    def _validate_property(self, value: Any, prop_schema: dict) -> bool:
        """Validate a single property."""
        prop_type = prop_schema.get("type")

        if prop_type == "string" and not isinstance(value, str):
            return False
        elif prop_type == "number" and not isinstance(value, (int, float)):
            return False
        elif prop_type == "integer" and not isinstance(value, int):
            return False
        elif prop_type == "boolean" and not isinstance(value, bool):
            return False
        elif prop_type == "array" and not isinstance(value, list):
            return False
        elif prop_type == "object" and not isinstance(value, dict):
            return False

        # Check min/max for numbers
        if isinstance(value, (int, float)):
            if "minimum" in prop_schema and value < prop_schema["minimum"]:
                return False
            if "maximum" in prop_schema and value > prop_schema["maximum"]:
                return False

        # Check length for strings
        if isinstance(value, str):
            if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
                return False
            if "maxLength" in prop_schema and len(value) > prop_schema["maxLength"]:
                return False

        return True

    def is_valid_email(self, email: str) -> bool:
        """
        Validate email address.

        Args:
            email: Email to validate

        Returns:
            True if valid email format
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def is_valid_url(self, url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid URL format
        """
        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, url))

    def is_valid_ipv4(self, ip: str) -> bool:
        """
        Validate IPv4 address.

        Args:
            ip: IP address to validate

        Returns:
            True if valid IPv4
        """
        pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return bool(re.match(pattern, ip))

    def get_validation_errors(self) -> list[str]:
        """Get validation errors from last validation."""
        return self._errors


class DataNormalizer:
    """
    Normalizes data by converting types and standardizing formats.
    """

    @staticmethod
    def normalize(data: Any, schema: Optional[dict] = None) -> Any:
        """
        Normalize data to match schema.

        Args:
            data: Data to normalize
            schema: Optional schema for normalization

        Returns:
            Normalized data
        """
        if schema is None:
            return data

        if isinstance(data, dict):
            normalized = {}
            properties = schema.get("properties", {})

            for key, value in data.items():
                if key in properties:
                    prop_schema = properties[key]
                    normalized[key] = DataNormalizer._normalize_value(value, prop_schema)
                else:
                    normalized[key] = value

            return normalized

        return data

    @staticmethod
    def _normalize_value(value: Any, schema: dict) -> Any:
        """Normalize a single value."""
        prop_type = schema.get("type")

        if prop_type == "string" and not isinstance(value, str):
            return str(value)
        elif prop_type == "integer" and not isinstance(value, int):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        elif prop_type == "number" and not isinstance(value, (int, float)):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        elif prop_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1", "on")
            return bool(value)

        return value

    @staticmethod
    def normalize_keys(data: dict, case_style: str = "snake_case") -> dict:
        """
        Normalize dictionary keys to specified case style.

        Args:
            data: Dictionary to normalize
            case_style: Target case style

        Returns:
            Dictionary with normalized keys
        """
        from mARCH.parsing.string_transform import StringTransform, CaseStyle

        normalized = {}

        for key, value in data.items():
            if case_style == "snake_case":
                new_key = StringTransform.to_snake_case(key)
            elif case_style == "camel_case":
                new_key = StringTransform.to_camel_case(key)
            elif case_style == "kebab_case":
                new_key = StringTransform.to_kebab_case(key)
            else:
                new_key = key

            normalized[new_key] = value

        return normalized

    @staticmethod
    def remove_nulls(data: dict) -> dict:
        """
        Remove null/None values from dictionary.

        Args:
            data: Dictionary to clean

        Returns:
            Dictionary with null values removed
        """
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def flatten(data: dict, parent_key: str = "", sep: str = ".") -> dict:
        """
        Flatten nested dictionary.

        Args:
            data: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys

        Returns:
            Flattened dictionary
        """
        items = []

        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(DataNormalizer.flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))

        return dict(items)


class SanitizationRules:
    """
    Sanitizes data by removing sensitive patterns.
    """

    # Common sensitive patterns
    PATTERNS = {
        "password": r'password["\']?\s*[:=]\s*["\']?([^"\'}\s]+)',
        "token": r'(token|api_key)["\']?\s*[:=]\s*["\']?([^"\'}\s]+)',
        "api_key": r'(api[_-]?key)["\']?\s*[:=]\s*["\']?([^"\'}\s]+)',
        "secret": r'(secret|client_secret)["\']?\s*[:=]\s*["\']?([^"\'}\s]+)',
        "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        "ssn": r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    }

    @staticmethod
    def sanitize(text: str, rules: Optional[list[str]] = None) -> str:
        """
        Sanitize text by removing sensitive patterns.

        Args:
            text: Text to sanitize
            rules: List of rules to apply (all if None)

        Returns:
            Sanitized text
        """
        if rules is None:
            rules = list(SanitizationRules.PATTERNS.keys())

        sanitized = text
        for rule in rules:
            if rule in SanitizationRules.PATTERNS:
                pattern = SanitizationRules.PATTERNS[rule]
                sanitized = re.sub(pattern, f"[REDACTED_{rule.upper()}]", sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def remove_pii(text: str) -> str:
        """
        Remove personally identifiable information.

        Args:
            text: Text to clean

        Returns:
            Text with PII removed
        """
        pii_rules = ["email", "credit_card", "ssn"]
        return SanitizationRules.sanitize(text, pii_rules)

    @staticmethod
    def sanitize_paths(paths: list[str]) -> list[str]:
        """
        Sanitize file paths.

        Args:
            paths: List of file paths

        Returns:
            List of sanitized paths
        """
        sanitized = []

        for path in paths:
            # Remove absolute paths, convert to relative
            if path.startswith("/"):
                path = path.lstrip("/")
            elif path.startswith("\\"):
                path = path.lstrip("\\")

            sanitized.append(path)

        return sanitized

    @staticmethod
    def sanitize_urls(urls: list[str]) -> list[str]:
        """
        Sanitize URLs by removing credentials.

        Args:
            urls: List of URLs

        Returns:
            List of sanitized URLs
        """
        sanitized = []

        for url in urls:
            try:
                parsed = urllib.parse.urlparse(url)
                # Reconstruct without credentials
                cleaned_url = urllib.parse.urlunparse((
                    parsed.scheme,
                    parsed.hostname or "",
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                ))
                sanitized.append(cleaned_url)
            except Exception:
                sanitized.append(url)

        return sanitized

    @staticmethod
    def redact_sensitive(data: dict, sensitive_keys: Optional[list[str]] = None) -> dict:
        """
        Redact sensitive values in dictionary.

        Args:
            data: Dictionary to redact
            sensitive_keys: List of keys to redact (password, token, etc. if None)

        Returns:
            Dictionary with sensitive values redacted
        """
        if sensitive_keys is None:
            sensitive_keys = ["password", "token", "secret", "api_key", "auth"]

        redacted = {}

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = value

        return redacted
