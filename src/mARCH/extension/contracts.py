"""Pydantic models for extension contracts and API."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .types import ExtensionType, PermissionType, SandboxLevel


class ExtensionCapability(BaseModel):
    """Declares a capability that an extension provides."""

    name: str = Field(..., description="Name of the capability")
    version: str = Field("1.0.0", description="Capability version")
    methods: list[str] = Field(default_factory=list, description="Methods provided")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters")


class ExtensionPermission(BaseModel):
    """Declares a permission requested by an extension."""

    type: PermissionType = Field(..., description="Permission type")
    resource: Optional[str] = Field(None, description="Specific resource (e.g., path pattern)")
    description: Optional[str] = Field(None, description="Why this permission is needed")


class ExtensionManifest(BaseModel):
    """Manifest defining an extension's metadata and requirements."""

    model_config = ConfigDict(use_enum_values=False)

    name: str = Field(..., description="Unique extension identifier")
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    display_name: str = Field(..., description="Human-readable extension name")
    description: str = Field(..., description="Extension description")
    author: Optional[str] = Field(None, description="Extension author")
    license: Optional[str] = Field(None, description="License type")
    homepage: Optional[str] = Field(None, description="Homepage URL")
    repository: Optional[str] = Field(None, description="Repository URL")
    
    # Extension configuration
    type: ExtensionType = Field(..., description="Extension type")
    entry_point: str = Field(..., description="Path to entry module/script")
    
    # Lifecycle and requirements
    dependencies: list[str] = Field(default_factory=list, description="Required extensions")
    required_version: Optional[str] = Field(None, description="Min mARCH version")
    
    # Security
    sandbox_level: SandboxLevel = Field(
        SandboxLevel.FILE_RESTRICTED, description="Sandboxing level"
    )
    permissions: list[ExtensionPermission] = Field(
        default_factory=list, description="Requested permissions"
    )
    
    # Capabilities
    capabilities: list[ExtensionCapability] = Field(
        default_factory=list, description="Provided capabilities"
    )
    
    # Configuration
    configuration_schema: Optional[dict[str, Any]] = Field(
        None, description="JSON Schema for configuration"
    )


class ExtensionConfig(BaseModel):
    """Runtime configuration for an extension."""

    model_config = ConfigDict(extra="allow")

    extension_name: str = Field(..., description="Extension identifier")
    enabled: bool = Field(True, description="Whether extension is enabled")
    auto_load: bool = Field(True, description="Load on startup")
    settings: dict[str, Any] = Field(default_factory=dict, description="Custom settings")


class ExtensionStatus(BaseModel):
    """Status information for a loaded extension."""

    name: str = Field(..., description="Extension name")
    version: str = Field(..., description="Extension version")
    status: str = Field(..., description="Current status")
    last_error: Optional[str] = Field(None, description="Last error if failed")
    load_time_ms: Optional[float] = Field(None, description="Load time in milliseconds")
    resource_usage: Optional[dict[str, Any]] = Field(None, description="Resource metrics")
