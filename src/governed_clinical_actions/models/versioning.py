"""Compatibility import surface for version policy helpers."""

from .base import (
    CURRENT_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    BoundaryModel,
    BoundaryValidationError,
    IncompatibleSchemaVersionError,
    SchemaVersionError,
    UnknownSchemaVersionError,
    VersionedEnvelope,
    VersionEnvelope,
    ensure_supported_schema_version,
    is_schema_version_compatible,
    validate_boundary_model,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "SUPPORTED_SCHEMA_VERSIONS",
    "BoundaryModel",
    "BoundaryValidationError",
    "IncompatibleSchemaVersionError",
    "SchemaVersionError",
    "UnknownSchemaVersionError",
    "VersionEnvelope",
    "VersionedEnvelope",
    "ensure_supported_schema_version",
    "is_schema_version_compatible",
    "validate_boundary_model",
]
