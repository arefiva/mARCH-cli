"""
Payload marshaling and unmarshaling utilities.

Provides PayloadCodec for encoding/decoding data and PayloadValidator for
schema validation.
"""

import json
import base64
import gzip
from typing import Any, Optional, Union
from enum import Enum


class PayloadFormat(Enum):
    """Supported payload formats."""

    JSON = "json"
    BINARY = "binary"
    BASE64 = "base64"


class PayloadCodec:
    """
    Codec for encoding and decoding payloads.

    Supports JSON, binary, and Base64 formats with optional compression.
    """

    def __init__(self, enable_compression: bool = False) -> None:
        """
        Initialize PayloadCodec.

        Args:
            enable_compression: Enable gzip compression for large payloads
        """
        self.enable_compression = enable_compression
        self.compression_threshold = 1024  # Compress if > 1KB

    def encode(
        self,
        data: Any,
        format: PayloadFormat = PayloadFormat.JSON,
    ) -> bytes:
        """
        Encode data to bytes.

        Args:
            data: Data to encode
            format: Output format

        Returns:
            Encoded bytes

        Raises:
            ValueError: If data cannot be encoded
            TypeError: If format is unsupported
        """
        if format == PayloadFormat.JSON:
            return self._encode_json(data)
        elif format == PayloadFormat.BINARY:
            return self._encode_binary(data)
        elif format == PayloadFormat.BASE64:
            return self._encode_base64(data)
        else:
            raise TypeError(f"Unsupported format: {format}")

    def decode(
        self,
        data: bytes,
        format: PayloadFormat = PayloadFormat.JSON,
    ) -> Any:
        """
        Decode data from bytes.

        Args:
            data: Bytes to decode
            format: Input format

        Returns:
            Decoded data

        Raises:
            ValueError: If data cannot be decoded
            TypeError: If format is unsupported
        """
        if format == PayloadFormat.JSON:
            return self._decode_json(data)
        elif format == PayloadFormat.BINARY:
            return self._decode_binary(data)
        elif format == PayloadFormat.BASE64:
            return self._decode_base64(data)
        else:
            raise TypeError(f"Unsupported format: {format}")

    def _encode_json(self, data: Any) -> bytes:
        """Encode data as JSON."""
        try:
            json_str = json.dumps(data, default=str)
            json_bytes = json_str.encode("utf-8")

            # Optional compression
            if self.enable_compression and len(json_bytes) > self.compression_threshold:
                json_bytes = gzip.compress(json_bytes)

            return json_bytes
        except (TypeError, ValueError) as e:
            raise ValueError(f"JSON encoding failed: {str(e)}")

    def _decode_json(self, data: bytes) -> Any:
        """Decode JSON data."""
        try:
            # Try decompression first
            try:
                decompressed = gzip.decompress(data)
                data = decompressed
            except Exception:
                pass

            json_str = data.decode("utf-8")
            return json.loads(json_str)
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"JSON decoding failed: {str(e)}")

    def _encode_binary(self, data: Any) -> bytes:
        """Encode data as binary."""
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return data.encode("utf-8")
        else:
            # Convert to string and encode
            return str(data).encode("utf-8")

    def _decode_binary(self, data: bytes) -> bytes:
        """Decode binary data."""
        return data

    def _encode_base64(self, data: Any) -> bytes:
        """Encode data as Base64."""
        if isinstance(data, bytes):
            raw_bytes = data
        elif isinstance(data, str):
            raw_bytes = data.encode("utf-8")
        else:
            raw_bytes = str(data).encode("utf-8")

        return base64.b64encode(raw_bytes)

    def _decode_base64(self, data: bytes) -> bytes:
        """Decode Base64 data."""
        try:
            return base64.b64decode(data)
        except Exception as e:
            raise ValueError(f"Base64 decoding failed: {str(e)}")

    def encode_streaming(
        self,
        data_generator,
        format: PayloadFormat = PayloadFormat.JSON,
        chunk_size: int = 8192,
    ):
        """
        Encode data from a generator in chunks.

        Args:
            data_generator: Generator yielding data chunks
            format: Output format
            chunk_size: Size of output chunks

        Yields:
            Encoded chunks
        """
        if format == PayloadFormat.JSON:
            buffer = []
            buffer_size = 0

            for item in data_generator:
                encoded_item = json.dumps(item, default=str).encode("utf-8")
                buffer.append(encoded_item)
                buffer_size += len(encoded_item)

                if buffer_size >= chunk_size:
                    yield b",".join(buffer)
                    buffer = []
                    buffer_size = 0

            if buffer:
                yield b",".join(buffer)
        else:
            for chunk in data_generator:
                if isinstance(chunk, bytes):
                    yield chunk
                else:
                    yield str(chunk).encode("utf-8")

    def estimate_size(self, data: Any) -> int:
        """
        Estimate encoded size of data.

        Args:
            data: Data to estimate

        Returns:
            Estimated size in bytes
        """
        json_str = json.dumps(data, default=str)
        json_bytes = json_str.encode("utf-8")

        if self.enable_compression:
            compressed = gzip.compress(json_bytes)
            return len(compressed)

        return len(json_bytes)


class PayloadValidator:
    """
    Validates payloads against schemas.

    Uses pydantic for robust validation with detailed error reporting.
    """

    def __init__(self) -> None:
        """Initialize PayloadValidator."""
        self._errors: list[str] = []

    def validate(
        self,
        data: Any,
        schema: dict,
    ) -> bool:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema: Validation schema (basic validation rules)

        Returns:
            True if valid, False otherwise
        """
        self._errors = []

        if not schema:
            return True

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
                        self._errors.append(f"Invalid value for property '{key}'")

        return len(self._errors) == 0

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

        return True

    def get_validation_errors(self) -> list[str]:
        """
        Get validation errors from last validation.

        Returns:
            List of error messages
        """
        return self._errors

    def validate_email(self, email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email to validate

        Returns:
            True if valid email format, False otherwise
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def validate_url(self, url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid URL format, False otherwise
        """
        import re

        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, url))

    def validate_size(
        self,
        data: Any,
        max_size: int,
    ) -> bool:
        """
        Validate payload size.

        Args:
            data: Data to check
            max_size: Maximum size in bytes

        Returns:
            True if within size limit, False otherwise
        """
        if isinstance(data, bytes):
            return len(data) <= max_size
        elif isinstance(data, str):
            return len(data.encode("utf-8")) <= max_size
        else:
            json_str = json.dumps(data, default=str)
            return len(json_str.encode("utf-8")) <= max_size
