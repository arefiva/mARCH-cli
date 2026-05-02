"""API call skill for HTTP requests."""

import logging
from typing import Any, Dict, Optional

from ..registry import Skill

logger = logging.getLogger(__name__)


class APICallSkill(Skill):
    """Makes HTTP API calls."""

    name = "api_call"
    version = "1.0.0"
    description = "Make HTTP requests to APIs"

    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request.

        Args:
            params: Parameters including 'url', 'method', and optional headers/body
            context: Optional execution context

        Returns:
            Result with response status and data
        """
        url = params.get("url")
        if not url:
            raise ValueError("Missing required parameter: url")

        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        body = params.get("body")
        timeout = params.get("timeout", 30)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                request_kwargs = {
                    "headers": headers,
                    "timeout": aiohttp.ClientTimeout(total=timeout),
                }

                if body:
                    request_kwargs["data"] = body

                async with session.request(method, url, **request_kwargs) as response:
                    text = await response.text()

                    return {
                        "url": url,
                        "method": method,
                        "status": response.status,
                        "headers": dict(response.headers),
                        "body": text,
                        "success": 200 <= response.status < 300,
                    }

        except ImportError:
            logger.error("aiohttp not installed. Cannot make API calls.")
            raise RuntimeError("aiohttp is required for API calls")
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters."""
        return "url" in params

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to request",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, etc.)",
                    "default": "GET",
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers",
                    "default": {},
                },
                "body": {
                    "type": "string",
                    "description": "Request body",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": 30,
                },
            },
            "required": ["url"],
        }
