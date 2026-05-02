"""Unit tests for payload serialization module."""

import pytest
from dataclasses import dataclass
from pydantic import BaseModel

from mARCH.networking.payload import (
    JsonCodec,
    PayloadCodecError,
    PayloadSerializer,
    serialize,
    deserialize,
)


@dataclass
class SampleDataclass:
    """Sample dataclass for testing."""
    name: str
    value: int


class SamplePydantic(BaseModel):
    """Sample Pydantic model for testing."""
    name: str
    value: int


class TestJsonCodec:
    """Tests for JSON codec."""

    def test_encode_dict(self):
        """Test encoding a dictionary."""
        codec = JsonCodec()
        data = {"key": "value", "number": 42}
        encoded = codec.encode(data)
        assert isinstance(encoded, bytes)
        assert b'"key"' in encoded

    def test_encode_list(self):
        """Test encoding a list."""
        codec = JsonCodec()
        data = [1, 2, 3, "test"]
        encoded = codec.encode(data)
        assert isinstance(encoded, bytes)

    def test_encode_pydantic(self):
        """Test encoding Pydantic model."""
        codec = JsonCodec()
        data = SamplePydantic(name="test", value=123)
        encoded = codec.encode(data)
        assert isinstance(encoded, bytes)

    def test_encode_dataclass(self):
        """Test encoding dataclass."""
        codec = JsonCodec()
        data = SampleDataclass(name="test", value=123)
        encoded = codec.encode(data)
        assert isinstance(encoded, bytes)

    def test_decode_dict(self):
        """Test decoding to dictionary."""
        codec = JsonCodec()
        data = {"key": "value", "number": 42}
        encoded = codec.encode(data)
        decoded = codec.decode(encoded)
        assert decoded == data

    def test_decode_list(self):
        """Test decoding to list."""
        codec = JsonCodec()
        data = [1, 2, 3, "test"]
        encoded = codec.encode(data)
        decoded = codec.decode(encoded)
        assert decoded == data

    def test_encode_invalid_type(self):
        """Test encoding invalid type raises error."""
        codec = JsonCodec()
        with pytest.raises(PayloadCodecError):
            codec.encode(set([1, 2, 3]))

    def test_decode_invalid_json(self):
        """Test decoding invalid JSON raises error."""
        codec = JsonCodec()
        with pytest.raises(PayloadCodecError):
            codec.decode(b"invalid json {")

    def test_media_type(self):
        """Test media type property."""
        codec = JsonCodec()
        assert codec.media_type == "application/json"


class TestPayloadSerializer:
    """Tests for PayloadSerializer."""

    def test_serialize_default(self):
        """Test serialization with default codec."""
        serializer = PayloadSerializer()
        data = {"test": "value"}
        result = serializer.serialize(data)
        assert isinstance(result, bytes)

    def test_deserialize_default(self):
        """Test deserialization with default codec."""
        serializer = PayloadSerializer()
        data = {"test": "value"}
        encoded = serializer.serialize(data)
        decoded = serializer.deserialize(encoded)
        assert decoded == data

    def test_serialize_explicit_codec(self):
        """Test serialization with explicit codec."""
        serializer = PayloadSerializer()
        data = {"test": "value"}
        result = serializer.serialize(data, codec="json")
        assert isinstance(result, bytes)

    def test_deserialize_explicit_codec(self):
        """Test deserialization with explicit codec."""
        serializer = PayloadSerializer()
        data = {"test": "value"}
        encoded = serializer.serialize(data)
        decoded = serializer.deserialize(encoded, codec="json")
        assert decoded == data

    def test_serialize_to_dict(self):
        """Test serialize_to_dict."""
        serializer = PayloadSerializer()
        data = {"test": "value"}
        result = serializer.serialize_to_dict(data)
        assert "content" in result
        assert "content_type" in result
        assert result["content_type"] == "application/json"

    def test_default_codec_change(self):
        """Test changing default codec."""
        serializer = PayloadSerializer()
        serializer.set_default_codec("json")
        data = {"test": "value"}
        result = serializer.serialize(data)
        assert isinstance(result, bytes)

    def test_invalid_codec(self):
        """Test using invalid codec raises error."""
        serializer = PayloadSerializer()
        with pytest.raises(KeyError):
            serializer.serialize({"test": "value"}, codec="invalid")

    def test_type_conversion(self):
        """Test type conversion during deserialization."""
        serializer = PayloadSerializer()
        data = {"name": "test", "value": 123}
        encoded = serializer.serialize(data)
        decoded = serializer.deserialize(encoded, target_type=SamplePydantic)
        assert isinstance(decoded, SamplePydantic)
        assert decoded.name == "test"

    def test_detect_codec_from_content_type(self):
        """Test codec detection from content type."""
        serializer = PayloadSerializer()
        data = {"test": "value"}
        encoded = serializer.serialize(data)
        decoded = serializer.deserialize(
            encoded,
            content_type_hint="application/json; charset=utf-8"
        )
        assert decoded == data

    def test_nested_data_structures(self):
        """Test serialization of nested data."""
        serializer = PayloadSerializer()
        data = {
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            "count": 2,
        }
        encoded = serializer.serialize(data)
        decoded = serializer.deserialize(encoded)
        assert decoded == data


class TestGlobalSerializer:
    """Tests for global serializer functions."""

    def test_serialize_global(self):
        """Test global serialize function."""
        data = {"test": "value"}
        result = serialize(data)
        assert isinstance(result, bytes)

    def test_deserialize_global(self):
        """Test global deserialize function."""
        data = {"test": "value"}
        encoded = serialize(data)
        decoded = deserialize(encoded)
        assert decoded == data

    def test_deserialize_with_type_conversion(self):
        """Test deserialization with type conversion."""
        data = {"name": "test", "value": 123}
        encoded = serialize(data)
        decoded = deserialize(encoded, target_type=SamplePydantic)
        assert isinstance(decoded, SamplePydantic)
