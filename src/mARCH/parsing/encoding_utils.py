"""
Encoding and decoding utilities for multiple formats.

Provides Encoder and Decoder for handling UTF-8, Base64, hex, and URL encoding.
"""

import base64
import urllib.parse
import codecs
from typing import Union, Optional
from enum import Enum


class EncodingFormat(Enum):
    """Supported encoding formats."""

    UTF8 = "utf-8"
    UTF16 = "utf-16"
    ASCII = "ascii"
    LATIN1 = "latin-1"
    BASE64 = "base64"
    HEX = "hex"
    URL_ENCODED = "url_encoded"


class Encoder:
    """
    Encodes data to various formats.

    Supports UTF-8, UTF-16, ASCII, Latin-1, Base64, hex, and URL encoding.
    """

    @staticmethod
    def encode(
        data: Union[str, bytes],
        format: EncodingFormat = EncodingFormat.UTF8,
    ) -> bytes:
        """
        Encode data to specified format.

        Args:
            data: Data to encode
            format: Target encoding format

        Returns:
            Encoded bytes

        Raises:
            UnicodeEncodeError: If encoding fails
            ValueError: If format is unsupported
        """
        # Convert to str if needed
        if isinstance(data, bytes):
            try:
                data = data.decode("utf-8")
            except UnicodeDecodeError:
                # If can't decode as UTF-8, treat as raw bytes
                pass

        if format == EncodingFormat.UTF8:
            if isinstance(data, bytes):
                return data
            return data.encode("utf-8")

        elif format == EncodingFormat.UTF16:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return data.encode("utf-16")

        elif format == EncodingFormat.ASCII:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return data.encode("ascii")

        elif format == EncodingFormat.LATIN1:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return data.encode("latin-1")

        elif format == EncodingFormat.BASE64:
            if isinstance(data, str):
                data = data.encode("utf-8")
            return base64.b64encode(data)

        elif format == EncodingFormat.HEX:
            if isinstance(data, str):
                data = data.encode("utf-8")
            return data.hex().encode("ascii")

        elif format == EncodingFormat.URL_ENCODED:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return urllib.parse.quote(data).encode("utf-8")

        else:
            raise ValueError(f"Unsupported encoding format: {format}")

    @staticmethod
    def encode_safe(
        data: str,
        format: EncodingFormat = EncodingFormat.UTF8,
    ) -> Optional[bytes]:
        """
        Encode data with error handling.

        Args:
            data: Data to encode
            format: Target encoding format

        Returns:
            Encoded bytes or None if encoding fails
        """
        try:
            return Encoder.encode(data, format)
        except (UnicodeEncodeError, ValueError, AttributeError):
            return None

    @staticmethod
    def auto_detect_encoding(data: bytes) -> EncodingFormat:
        """
        Auto-detect encoding of data.

        Args:
            data: Data to analyze

        Returns:
            Detected encoding format
        """
        # Try common encodings
        for encoding in [
            EncodingFormat.UTF8,
            EncodingFormat.UTF16,
            EncodingFormat.ASCII,
            EncodingFormat.LATIN1,
        ]:
            try:
                data.decode(encoding.value)
                return encoding
            except UnicodeDecodeError:
                continue

        # If all text encodings fail, might be binary
        return EncodingFormat.BASE64


class Decoder:
    """
    Decodes data from various formats.

    Supports UTF-8, UTF-16, ASCII, Latin-1, Base64, hex, and URL encoding.
    """

    @staticmethod
    def decode(
        data: bytes,
        format: EncodingFormat = EncodingFormat.UTF8,
    ) -> Union[str, bytes]:
        """
        Decode data from specified format.

        Args:
            data: Data to decode
            format: Source encoding format

        Returns:
            Decoded string or bytes

        Raises:
            UnicodeDecodeError: If decoding fails
            ValueError: If format is unsupported or data is invalid
        """
        if format == EncodingFormat.UTF8:
            return data.decode("utf-8")

        elif format == EncodingFormat.UTF16:
            return data.decode("utf-16")

        elif format == EncodingFormat.ASCII:
            return data.decode("ascii")

        elif format == EncodingFormat.LATIN1:
            return data.decode("latin-1")

        elif format == EncodingFormat.BASE64:
            decoded = base64.b64decode(data)
            # Try to return as string
            try:
                return decoded.decode("utf-8")
            except UnicodeDecodeError:
                return decoded

        elif format == EncodingFormat.HEX:
            # Decode hex
            hex_str = data.decode("ascii")
            decoded = bytes.fromhex(hex_str)
            try:
                return decoded.decode("utf-8")
            except UnicodeDecodeError:
                return decoded

        elif format == EncodingFormat.URL_ENCODED:
            decoded = urllib.parse.unquote(data.decode("utf-8"))
            return decoded

        else:
            raise ValueError(f"Unsupported decoding format: {format}")

    @staticmethod
    def decode_safe(
        data: bytes,
        format: EncodingFormat = EncodingFormat.UTF8,
    ) -> Optional[Union[str, bytes]]:
        """
        Decode data with error handling.

        Args:
            data: Data to decode
            format: Source encoding format

        Returns:
            Decoded data or None if decoding fails
        """
        try:
            return Decoder.decode(data, format)
        except (UnicodeDecodeError, ValueError, binascii.Error):
            return None

    @staticmethod
    def detect_encoding(data: bytes) -> str:
        """
        Detect encoding of byte data.

        Args:
            data: Data to analyze

        Returns:
            Detected encoding name (e.g., 'utf-8')
        """
        # Try common encodings in order
        encodings = ["utf-8", "utf-16", "ascii", "latin-1"]

        for encoding in encodings:
            try:
                data.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue

        # If no text encoding works, might be binary
        return "binary"

    @staticmethod
    def validate_encoding(
        data: bytes,
        format: EncodingFormat = EncodingFormat.UTF8,
    ) -> bool:
        """
        Validate that data is properly encoded.

        Args:
            data: Data to validate
            format: Expected encoding format

        Returns:
            True if data is valid for the format, False otherwise
        """
        try:
            Decoder.decode(data, format)
            return True
        except (UnicodeDecodeError, ValueError):
            return False


# Import binascii for error handling
import binascii


class EncodingConverter:
    """
    Converts data between different encoding formats.
    """

    @staticmethod
    def convert(
        data: Union[str, bytes],
        from_format: EncodingFormat,
        to_format: EncodingFormat,
    ) -> Union[str, bytes]:
        """
        Convert data from one format to another.

        Args:
            data: Data to convert
            from_format: Source format
            to_format: Target format

        Returns:
            Converted data

        Raises:
            UnicodeDecodeError: If conversion fails
        """
        # Decode from source format
        if isinstance(data, str):
            data = data.encode("utf-8") if from_format != EncodingFormat.URL_ENCODED else data

        # First decode to string/bytes
        if from_format == EncodingFormat.BASE64:
            decoded = base64.b64decode(data)
        elif from_format == EncodingFormat.HEX:
            hex_str = data.decode("ascii") if isinstance(data, bytes) else data
            decoded = bytes.fromhex(hex_str)
        elif from_format == EncodingFormat.URL_ENCODED:
            url_str = data.decode("utf-8") if isinstance(data, bytes) else data
            decoded = urllib.parse.unquote(url_str).encode("utf-8")
        else:
            # Text encoding
            if isinstance(data, str):
                decoded = data
            else:
                decoded = data.decode(from_format.value)

        # Now encode to target format
        if isinstance(decoded, str):
            decoded_bytes = decoded.encode("utf-8")
        else:
            decoded_bytes = decoded

        return Encoder.encode(decoded_bytes, to_format)

    @staticmethod
    def convert_safe(
        data: Union[str, bytes],
        from_format: EncodingFormat,
        to_format: EncodingFormat,
    ) -> Optional[Union[str, bytes]]:
        """
        Convert data with error handling.

        Args:
            data: Data to convert
            from_format: Source format
            to_format: Target format

        Returns:
            Converted data or None if conversion fails
        """
        try:
            return EncodingConverter.convert(data, from_format, to_format)
        except (UnicodeDecodeError, ValueError, binascii.Error):
            return None
