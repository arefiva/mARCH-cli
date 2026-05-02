"""Payload serialization and deserialization module.

Handles multiple serialization formats for cross-component communication.
Supports JSON and extensible codec system for custom formats.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional, Type, TypeVar, Union

from pydantic import BaseModel

T = TypeVar("T")


class PayloadCodec(ABC):
    """Abstract base class for payload codecs."""

    @abstractmethod
    def encode(self, data: Any) -> bytes:
        """Encode data to bytes.

        Args:
            data: Data to encode.

        Returns:
            Encoded data as bytes.

        Raises:
            PayloadCodecError: If encoding fails.
        """
        pass

    @abstractmethod
    def decode(self, data: bytes) -> Any:
        """Decode bytes to data.

        Args:
            data: Bytes to decode.

        Returns:
            Decoded data.

        Raises:
            PayloadCodecError: If decoding fails.
        """
        pass

    @property
    @abstractmethod
    def media_type(self) -> str:
        """Get the media type for this codec.

        Returns:
            Media type string (e.g., 'application/json').
        """
        pass


class PayloadCodecError(Exception):
    """Exception raised for codec encoding/decoding errors."""

    pass


class JsonCodec(PayloadCodec):
    """JSON serialization codec."""

    def encode(self, data: Any) -> bytes:
        """Encode data to JSON bytes.

        Args:
            data: Data to encode (must be JSON-serializable).

        Returns:
            JSON-encoded bytes.

        Raises:
            PayloadCodecError: If data is not JSON-serializable.
        """
        try:
            json_str = json.dumps(self._prepare_data(data), separators=(",", ":"))
            return json_str.encode("utf-8")
        except (TypeError, ValueError) as e:
            raise PayloadCodecError(f"Failed to encode data to JSON: {e}") from e

    def decode(self, data: bytes) -> Any:
        """Decode JSON bytes to data.

        Args:
            data: JSON-encoded bytes.

        Returns:
            Decoded data.

        Raises:
            PayloadCodecError: If data is not valid JSON.
        """
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise PayloadCodecError(f"Failed to decode JSON: {e}") from e

    @property
    def media_type(self) -> str:
        """Get media type for JSON codec."""
        return "application/json"

    def _prepare_data(self, data: Any) -> Any:
        """Prepare data for JSON serialization.

        Converts Pydantic models and dataclasses to dicts.

        Args:
            data: Data to prepare.

        Returns:
            JSON-serializable data.
        """
        if isinstance(data, BaseModel):
            return data.model_dump()
        elif isinstance(data, dict):
            return {k: self._prepare_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._prepare_data(item) for item in data]
        elif is_dataclass(data) and not isinstance(data, type):
            return self._prepare_data(asdict(data))
        else:
            return data


class PayloadSerializer:
    """Main serialization interface.

    Provides automatic format detection and serialization/deserialization
    with support for multiple codecs.
    """

    def __init__(self):
        """Initialize serializer with default codecs."""
        self._codecs: Dict[str, PayloadCodec] = {}
        self._default_codec = "json"

        # Register default codecs
        self.register_codec("json", JsonCodec())

    def register_codec(self, name: str, codec: PayloadCodec) -> None:
        """Register a codec.

        Args:
            name: Name/identifier for the codec.
            codec: Codec instance.
        """
        self._codecs[name] = codec

    def set_default_codec(self, name: str) -> None:
        """Set the default codec for serialization.

        Args:
            name: Name of the codec to set as default.

        Raises:
            KeyError: If codec is not registered.
        """
        if name not in self._codecs:
            raise KeyError(f"Codec '{name}' not registered")
        self._default_codec = name

    def serialize(
        self,
        data: Any,
        codec: Optional[str] = None,
        content_type_hint: Optional[str] = None,
    ) -> bytes:
        """Serialize data to bytes.

        Args:
            data: Data to serialize.
            codec: Codec name to use. Uses default if not specified.
            content_type_hint: Optional hint for format detection.

        Returns:
            Serialized data as bytes.

        Raises:
            PayloadCodecError: If serialization fails.
            KeyError: If specified codec not found.
        """
        codec_name = codec or self._default_codec
        if content_type_hint:
            codec_name = self._detect_codec_from_content_type(content_type_hint) or codec_name

        if codec_name not in self._codecs:
            raise KeyError(f"Codec '{codec_name}' not registered")

        return self._codecs[codec_name].encode(data)

    def deserialize(
        self,
        data: bytes,
        codec: Optional[str] = None,
        content_type_hint: Optional[str] = None,
        target_type: Optional[Type[T]] = None,
    ) -> Any:
        """Deserialize bytes to data.

        Args:
            data: Bytes to deserialize.
            codec: Codec name to use. Uses default if not specified.
            content_type_hint: Optional hint for format detection.
            target_type: Optional target type for validation/conversion.

        Returns:
            Deserialized data.

        Raises:
            PayloadCodecError: If deserialization fails.
            KeyError: If specified codec not found.
        """
        codec_name = codec or self._default_codec
        if content_type_hint:
            codec_name = self._detect_codec_from_content_type(content_type_hint) or codec_name

        if codec_name not in self._codecs:
            raise KeyError(f"Codec '{codec_name}' not registered")

        decoded = self._codecs[codec_name].decode(data)

        # Type conversion if target type specified
        if target_type:
            decoded = self._convert_type(decoded, target_type)

        return decoded

    def serialize_to_dict(self, data: Any) -> Dict[str, Any]:
        """Serialize data and return as dictionary.

        Args:
            data: Data to serialize.

        Returns:
            Dictionary with 'content' and 'content_type' keys.
        """
        serialized = self.serialize(data)
        codec = self._codecs[self._default_codec]
        return {
            "content": serialized,
            "content_type": codec.media_type,
        }

    def _detect_codec_from_content_type(self, content_type: str) -> Optional[str]:
        """Detect codec from content type.

        Args:
            content_type: Content type string.

        Returns:
            Codec name if found, None otherwise.
        """
        for name, codec in self._codecs.items():
            if codec.media_type in content_type:
                return name
        return None

    def _convert_type(self, data: Any, target_type: Type[T]) -> T:
        """Convert data to target type.

        Args:
            data: Data to convert.
            target_type: Target type to convert to.

        Returns:
            Converted data.

        Raises:
            PayloadCodecError: If conversion fails.
        """
        if target_type is dict or target_type is Any:
            return data
        if isinstance(data, target_type):
            return data

        try:
            if hasattr(target_type, "model_validate"):  # Pydantic v2
                return target_type.model_validate(data)
            elif hasattr(target_type, "parse_obj"):  # Pydantic v1 fallback
                return target_type.parse_obj(data)
            else:
                return target_type(**data) if isinstance(data, dict) else target_type(data)
        except Exception as e:
            raise PayloadCodecError(
                f"Failed to convert data to {target_type.__name__}: {e}"
            ) from e


# Global serializer instance
_global_serializer = PayloadSerializer()


def get_serializer() -> PayloadSerializer:
    """Get the global serializer instance.

    Returns:
        Global PayloadSerializer instance.
    """
    return _global_serializer


def serialize(data: Any, codec: Optional[str] = None) -> bytes:
    """Serialize data using the global serializer.

    Args:
        data: Data to serialize.
        codec: Optional codec name.

    Returns:
        Serialized data as bytes.
    """
    return _global_serializer.serialize(data, codec)


def deserialize(data: bytes, codec: Optional[str] = None, target_type: Optional[Type[T]] = None) -> Any:
    """Deserialize bytes using the global serializer.

    Args:
        data: Bytes to deserialize.
        codec: Optional codec name.
        target_type: Optional target type for conversion.

    Returns:
        Deserialized data.
    """
    return _global_serializer.deserialize(data, codec, target_type=target_type)
