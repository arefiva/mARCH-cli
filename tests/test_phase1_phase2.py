"""Comprehensive tests for Phase 1 and Phase 2 modules."""

import pytest
import asyncio
import json
import tempfile
import os
from pathlib import Path

# Phase 1 imports
from mARCH.core.stream_buffer import StreamBuffer, StreamManager, StreamMode
from mARCH.core.shell_executor import ShellExecutor, CommandOptions, CommandResult, CaptureMode, ShellType
from mARCH.core.process_manager import ProcessManager, ProcessStatus
from mARCH.core.async_executor import TaskPool, CancelToken, TaskPriority
from mARCH.core.payload_handler import PayloadCodec, PayloadValidator, PayloadFormat

# Phase 2 imports
from mARCH.parsing.command_parser import CommandParser, ParsedCommand
from mARCH.parsing.text_parser import TextParser, TextFormat
from mARCH.parsing.encoding_utils import Encoder, Decoder, EncodingFormat
from mARCH.parsing.string_transform import StringTransform, TextFormatter, CaseStyle
from mARCH.parsing.data_validation import DataValidator, DataNormalizer, SanitizationRules


# ============================================================================
# Phase 1: Core Infrastructure Tests
# ============================================================================

class TestStreamBuffer:
    """Test StreamBuffer functionality."""

    @pytest.mark.asyncio
    async def test_stream_buffer_write_read(self):
        """Test basic write and read operations."""
        buffer = StreamBuffer(mode=StreamMode.TEXT)
        
        # Write data
        bytes_written = await buffer.write("Hello, World!")
        assert bytes_written == 13
        
        # Read data
        data = await buffer.read()
        assert data == "Hello, World!"

    @pytest.mark.asyncio
    async def test_stream_buffer_binary_mode(self):
        """Test binary mode."""
        buffer = StreamBuffer(mode=StreamMode.BINARY)
        
        # Write bytes
        bytes_written = await buffer.write(b"test data")
        assert bytes_written == 9
        
        # Read bytes
        data = await buffer.read()
        assert data == b"test data"

    @pytest.mark.asyncio
    async def test_stream_buffer_pause_resume(self):
        """Test pause/resume functionality."""
        buffer = StreamBuffer()
        
        buffer.pause()
        assert buffer.is_paused is True
        
        buffer.resume()
        assert buffer.is_paused is False

    @pytest.mark.asyncio
    async def test_stream_buffer_close(self):
        """Test close functionality."""
        buffer = StreamBuffer()
        
        await buffer.close()
        assert buffer.is_closed is True
        
        # Should not be able to write after close
        with pytest.raises(RuntimeError):
            await buffer.write("test")


class TestShellExecutor:
    """Test ShellExecutor functionality."""

    @pytest.mark.asyncio
    async def test_shell_executor_basic(self):
        """Test basic command execution."""
        executor = ShellExecutor()
        
        result = await executor.execute("echo 'hello'")
        
        assert result.return_code == 0
        assert "hello" in result.stdout
        assert isinstance(result.execution_time, float)

    @pytest.mark.asyncio
    async def test_shell_executor_with_options(self):
        """Test command execution with options."""
        executor = ShellExecutor()
        
        options = CommandOptions(
            shell=ShellType.BASH,
            capture_mode=CaptureMode.BOTH,
        )
        
        result = await executor.execute("echo 'test'", options)
        
        assert result.return_code == 0
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_shell_executor_invalid_command(self):
        """Test invalid command handling."""
        executor = ShellExecutor()
        
        with pytest.raises(ValueError):
            await executor.execute("")

    @pytest.mark.asyncio
    async def test_shell_executor_timeout(self):
        """Test timeout handling."""
        executor = ShellExecutor()
        
        options = CommandOptions(timeout=0.1)
        
        # Command that takes longer than timeout
        with pytest.raises(TimeoutError):
            await executor.execute("sleep 5", options)

    def test_shell_executor_validate_command(self):
        """Test command validation."""
        assert ShellExecutor.validate_command("echo 'test'") is True
        assert ShellExecutor.validate_command("") is False


class TestProcessManager:
    """Test ProcessManager functionality."""

    @pytest.mark.asyncio
    async def test_process_manager_register(self):
        """Test process registration."""
        manager = ProcessManager()
        
        # Get current process ID
        pid = os.getpid()
        
        process_info = await manager.register_process(pid, {"test": "metadata"})
        
        assert process_info.pid == pid
        assert process_info.metadata == {"test": "metadata"}

    @pytest.mark.asyncio
    async def test_process_manager_get_info(self):
        """Test getting process info."""
        manager = ProcessManager()
        
        pid = os.getpid()
        await manager.register_process(pid)
        
        info = manager.get_process_info(pid)
        assert info is not None
        assert info.pid == pid

    @pytest.mark.asyncio
    async def test_process_manager_cleanup(self):
        """Test cleanup."""
        manager = ProcessManager()
        
        pid = os.getpid()
        await manager.register_process(pid)
        
        await manager.cleanup_all()
        
        # Should be empty after cleanup
        assert len(manager.get_all_processes()) == 0


class TestAsyncExecutor:
    """Test async executor functionality."""

    @pytest.mark.asyncio
    async def test_task_pool_submit(self):
        """Test task submission."""
        pool = TaskPool(max_concurrency=2)
        
        async def dummy_task(x):
            await asyncio.sleep(0.01)
            return x * 2
        
        result = await pool.submit(dummy_task(5))
        
        assert result == 10
        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_task_pool_map(self):
        """Test map functionality."""
        pool = TaskPool(max_concurrency=2)
        
        async def double(x):
            return x * 2
        
        results = await pool.map(double, [1, 2, 3, 4, 5])
        
        assert results == [2, 4, 6, 8, 10]
        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_cancel_token(self):
        """Test cancel token functionality."""
        token = CancelToken()
        
        assert token.is_cancelled() is False
        
        token.cancel()
        
        assert token.is_cancelled() is True

    @pytest.mark.asyncio
    async def test_cancel_token_propagation(self):
        """Test parent-child cancellation propagation."""
        parent = CancelToken()
        child = parent.create_child()
        
        parent.cancel()
        
        assert child.is_cancelled() is True


class TestPayloadHandler:
    """Test payload handling functionality."""

    def test_payload_codec_json(self):
        """Test JSON encoding/decoding."""
        codec = PayloadCodec()
        
        data = {"key": "value", "number": 42}
        
        encoded = codec.encode(data, PayloadFormat.JSON)
        assert isinstance(encoded, bytes)
        
        decoded = codec.decode(encoded, PayloadFormat.JSON)
        assert decoded == data

    def test_payload_codec_base64(self):
        """Test Base64 encoding/decoding."""
        codec = PayloadCodec()
        
        data = b"Hello, World!"
        
        encoded = codec.encode(data, PayloadFormat.BASE64)
        assert isinstance(encoded, bytes)
        
        # Base64 encoded
        import base64
        assert base64.b64decode(encoded) == data

    def test_payload_validator_email(self):
        """Test email validation."""
        validator = PayloadValidator()
        
        assert validator.validate_email("test@example.com") is True
        assert validator.validate_email("invalid-email") is False

    def test_payload_validator_url(self):
        """Test URL validation."""
        validator = PayloadValidator()
        
        assert validator.validate_url("https://example.com") is True
        assert validator.validate_url("not a url") is False

    def test_payload_validator_size(self):
        """Test size validation."""
        validator = PayloadValidator()
        
        data = "test"
        assert validator.validate_size(data, 100) is True
        assert validator.validate_size(data, 2) is False


# ============================================================================
# Phase 2: Parsing & Data Processing Tests
# ============================================================================

class TestCommandParser:
    """Test command parsing functionality."""

    def test_command_parser_basic(self):
        """Test basic command parsing."""
        parser = CommandParser()
        
        parsed = parser.parse("git commit -m 'test'")
        
        assert parsed.command_name == "git"
        assert "commit" in parsed.positionals

    def test_command_parser_flags(self):
        """Test flag parsing."""
        parser = CommandParser()
        
        parsed = parser.parse("cmd --verbose --output=file.txt")
        
        assert parsed.get_flag("--verbose") is not None
        assert parsed.get_flag("--output") == "file.txt"

    def test_command_parser_validation(self):
        """Test command validation."""
        parser = CommandParser()
        
        is_valid, errors = parser.validate_syntax("echo 'test'")
        assert is_valid is True
        assert len(errors) == 0

    def test_command_parser_subcommand(self):
        """Test subcommand extraction."""
        parser = CommandParser()
        
        main, sub = parser.parse_subcommand("git commit -m 'test'")
        
        assert main == "git"
        assert sub == "commit"


class TestTextParser:
    """Test text parsing functionality."""

    def test_text_parser_markdown_detection(self):
        """Test markdown format detection."""
        parser = TextParser()
        
        markdown_text = "# Header\nSome content"
        format = parser.detect_format(markdown_text)
        
        assert format == TextFormat.MARKDOWN

    def test_text_parser_json_detection(self):
        """Test JSON format detection."""
        parser = TextParser()
        
        json_text = '{"key": "value"}'
        format = parser.detect_format(json_text)
        
        assert format == TextFormat.JSON

    def test_text_parser_code_block_extraction(self):
        """Test code block extraction."""
        parser = TextParser()
        
        text = '```python\nprint("hello")\n```'
        blocks = parser.extract_code_blocks(text)
        
        assert len(blocks) > 0
        assert blocks[0].language == "python"

    def test_text_parser_markdown_parsing(self):
        """Test markdown parsing."""
        parser = TextParser()
        
        markdown_text = "# Header 1\nContent 1\n## Header 2\nContent 2"
        parsed = parser.parse(markdown_text)
        
        assert parsed.format == TextFormat.MARKDOWN
        assert len(parsed.sections) > 0


class TestEncoding:
    """Test encoding/decoding functionality."""

    def test_encoder_utf8(self):
        """Test UTF-8 encoding."""
        text = "Hello, World!"
        encoded = Encoder.encode(text, EncodingFormat.UTF8)
        
        assert isinstance(encoded, bytes)
        assert encoded == text.encode("utf-8")

    def test_encoder_base64(self):
        """Test Base64 encoding."""
        text = "Hello, World!"
        encoded = Encoder.encode(text, EncodingFormat.BASE64)
        
        assert isinstance(encoded, bytes)

    def test_decoder_utf8(self):
        """Test UTF-8 decoding."""
        encoded = b"Hello, World!"
        decoded = Decoder.decode(encoded, EncodingFormat.UTF8)
        
        assert decoded == "Hello, World!"

    def test_encoding_detection(self):
        """Test encoding detection."""
        encoded = "Hello".encode("utf-8")
        detected = Decoder.detect_encoding(encoded)
        
        assert detected == "utf-8"


class TestStringTransform:
    """Test string transformation functionality."""

    def test_to_camel_case(self):
        """Test camelCase conversion."""
        result = StringTransform.to_camel_case("hello_world")
        assert result == "helloWorld"

    def test_to_snake_case(self):
        """Test snake_case conversion."""
        result = StringTransform.to_snake_case("helloWorld")
        assert result == "hello_world"

    def test_to_kebab_case(self):
        """Test kebab-case conversion."""
        result = StringTransform.to_kebab_case("hello_world")
        assert result == "hello-world"

    def test_to_pascal_case(self):
        """Test PascalCase conversion."""
        result = StringTransform.to_pascal_case("hello_world")
        assert result == "HelloWorld"

    def test_truncate(self):
        """Test string truncation."""
        result = StringTransform.truncate("Hello, World!", 5, "...")
        assert len(result) == 5

    def test_text_formatter(self):
        """Test text formatting."""
        template = "Hello, {name}!"
        result = TextFormatter.format(template, name="World")
        
        assert result == "Hello, World!"


class TestDataValidation:
    """Test data validation functionality."""

    def test_data_validator_email(self):
        """Test email validation."""
        validator = DataValidator()
        
        assert validator.is_valid_email("test@example.com") is True
        assert validator.is_valid_email("invalid") is False

    def test_data_validator_url(self):
        """Test URL validation."""
        validator = DataValidator()
        
        assert validator.is_valid_url("https://example.com") is True
        assert validator.is_valid_url("not a url") is False

    def test_data_normalizer_snake_case(self):
        """Test key normalization."""
        data = {"firstName": "John", "lastName": "Doe"}
        normalized = DataNormalizer.normalize_keys(data, "snake_case")
        
        assert "first_name" in normalized
        assert "last_name" in normalized

    def test_data_normalizer_remove_nulls(self):
        """Test null removal."""
        data = {"key1": "value1", "key2": None, "key3": "value3"}
        cleaned = DataNormalizer.remove_nulls(data)
        
        assert len(cleaned) == 2
        assert "key2" not in cleaned

    def test_sanitization_remove_pii(self):
        """Test PII removal."""
        text = "Email: test@example.com"
        sanitized = SanitizationRules.remove_pii(text)
        
        assert "test@example.com" not in sanitized


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_phase1_workflow():
    """Test Phase 1 workflow integration."""
    # Test stream buffer with shell executor
    executor = ShellExecutor()
    
    result = await executor.execute("echo 'test data'")
    
    assert result.return_code == 0
    assert len(result.stdout) > 0


def test_phase2_workflow():
    """Test Phase 2 workflow integration."""
    # Parse command
    parser = CommandParser()
    parsed = parser.parse("process --input file.txt --verbose")
    
    # Get values
    input_file = parsed.get_flag("--input")
    assert input_file == "file.txt"
    
    # Transform command name
    transformed = StringTransform.to_camel_case(parsed.command_name)
    assert isinstance(transformed, str)


@pytest.mark.asyncio
async def test_integration_stream_and_shell():
    """Test integration of stream buffer and shell executor."""
    executor = ShellExecutor()
    
    # Create stream manager
    manager = StreamManager()
    
    # Execute command
    result = await executor.execute("echo 'integration test'")
    
    assert result.return_code == 0
    assert "integration test" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
