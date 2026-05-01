"""
AI model API client for conversation and code analysis.

Provides interface to Claude API with streaming support, function calling,
and multi-model management.
"""

import os
from abc import ABC, abstractmethod
from collections.abc import Generator


class AIModel(ABC):
    """Abstract base class for AI models."""

    def __init__(self, model_name: str, api_key: str | None = None):
        """Initialize AI model."""
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Get completion from model."""
        pass

    @abstractmethod
    def stream_complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """Stream completion from model."""
        pass

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name


class ClaudeAIModel(AIModel):
    """Claude AI model via Anthropic API."""

    def __init__(
        self,
        model_name: str = "claude-sonnet-4.5",
        api_key: str | None = None,
    ):
        """Initialize Claude model."""
        super().__init__(model_name, api_key)
        self._ensure_client_available()

    def _ensure_client_available(self) -> None:
        """Ensure Anthropic client is available."""
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )

    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Get completion from Claude."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("Anthropic client not available")

        client = anthropic.Anthropic(api_key=self.api_key)

        response = client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,  # type: ignore[arg-type]
        )

        # Handle response content properly - TextBlock has .text attribute
        if response.content and len(response.content) > 0:
            content = response.content[0]
            if hasattr(content, 'text'):
                return content.text
        return ""

    def stream_complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """Stream completion from Claude."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("Anthropic client not available")

        client = anthropic.Anthropic(api_key=self.api_key)

        with client.messages.stream(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            for text in stream.text_stream:
                yield text


class AIModelFactory:
    """Factory for creating AI models."""

    AVAILABLE_MODELS = {
        "claude-opus-4-1": "Claude Opus 4.1",
    }

    @staticmethod
    def create_model(
        model_name: str,
        api_key: str | None = None,
    ) -> AIModel:
        """Create AI model instance."""
        if model_name.startswith("claude"):
            return ClaudeAIModel(model_name, api_key)
        else:
            raise ValueError(f"Unknown model: {model_name}")

    @staticmethod
    def list_available_models() -> list[str]:
        """List available models."""
        return list(AIModelFactory.AVAILABLE_MODELS.keys())


class ConversationClient:
    """Client for multi-turn conversations with AI."""

    def __init__(
        self,
        model_name: str = "claude-sonnet-4.5",
        api_key: str | None = None,
    ):
        """Initialize conversation client."""
        self.model = AIModelFactory.create_model(model_name, api_key)
        self.temperature = 0.7
        self.max_tokens = 2048

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send chat request to model."""
        temp = temperature or self.temperature
        tokens = max_tokens or self.max_tokens

        return self.model.complete(messages, max_tokens=tokens, temperature=temp)

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Stream chat response from model."""
        temp = temperature or self.temperature
        tokens = max_tokens or self.max_tokens

        yield from self.model.stream_complete(
            messages, max_tokens=tokens, temperature=temp
        )

    def set_temperature(self, temperature: float) -> None:
        """Set temperature for responses."""
        self.temperature = max(0.0, min(2.0, temperature))

    def set_max_tokens(self, max_tokens: int) -> None:
        """Set max tokens for responses."""
        self.max_tokens = max(1, max_tokens)

    def get_model_name(self) -> str:
        """Get current model name."""
        return self.model.get_model_name()


class CodeAnalysisClient:
    """Specialized client for code analysis and suggestions."""

    def __init__(
        self,
        model_name: str = "claude-sonnet-4.5",
        api_key: str | None = None,
    ):
        """Initialize code analysis client."""
        self.conversation = ConversationClient(model_name, api_key)

    def analyze_code(
        self,
        code: str,
        language: str,
        query: str,
    ) -> str:
        """
        Analyze code and provide insights.

        Args:
            code: Source code to analyze
            language: Programming language
            query: Analysis query

        Returns:
            Analysis result
        """
        messages = [
            {
                "role": "system",
                "content": f"You are a code analysis expert specializing in {language}.",
            },
            {
                "role": "user",
                "content": f"""Please analyze the following {language} code:

```{language}
{code}
```

{query}""",
            },
        ]

        return self.conversation.chat(messages)

    def suggest_improvements(
        self,
        code: str,
        language: str,
    ) -> str:
        """
        Suggest code improvements.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Suggestions
        """
        return self.analyze_code(
            code,
            language,
            "Suggest improvements for this code, focusing on:\n"
            "1. Performance\n"
            "2. Readability\n"
            "3. Best practices\n"
            "4. Error handling",
        )

    def explain_code(
        self,
        code: str,
        language: str,
    ) -> str:
        """
        Explain code functionality.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Explanation
        """
        return self.analyze_code(
            code,
            language,
            "Explain what this code does in detail.",
        )

    def find_bugs(
        self,
        code: str,
        language: str,
    ) -> str:
        """
        Find potential bugs in code.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Bug report
        """
        return self.analyze_code(
            code,
            language,
            "Find potential bugs or issues in this code. Be specific and explain each issue.",
        )


_conversation_client_instance: ConversationClient | None = None
_code_analysis_client_instance: CodeAnalysisClient | None = None


def get_conversation_client() -> ConversationClient:
    """Get or create singleton ConversationClient."""
    global _conversation_client_instance
    if _conversation_client_instance is None:
        _conversation_client_instance = ConversationClient()
    return _conversation_client_instance


def get_code_analysis_client() -> CodeAnalysisClient:
    """Get or create singleton CodeAnalysisClient."""
    global _code_analysis_client_instance
    if _code_analysis_client_instance is None:
        _code_analysis_client_instance = CodeAnalysisClient()
    return _code_analysis_client_instance
