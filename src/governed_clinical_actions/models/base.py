"""Shared rules for serialized, versioned boundary models.

E1 deliberately keeps the wire contract closed.  Every boundary object has a
literal schema version and rejects fields that are not part of that version.
Adding a future schema version therefore requires an explicit model and
migration decision instead of silently reinterpreting an old payload.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import Enum
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

CURRENT_SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = frozenset({CURRENT_SCHEMA_VERSION})
SchemaVersion = Literal[1]


class IncompatibleSchemaVersionError(ValueError):
    """Raised when a boundary payload uses an unsupported schema version."""

    def __init__(self, version: object, supported: frozenset[int] = SUPPORTED_SCHEMA_VERSIONS):
        self.version = version
        self.supported = supported
        super().__init__(
            f"Unsupported schema_version={version!r}; supported versions are "
            f"{sorted(supported)}"
        )


UnknownSchemaVersionError = IncompatibleSchemaVersionError
SchemaVersionError = IncompatibleSchemaVersionError


class BoundaryValidationError(ValueError):
    """Stable application error for malformed serialized boundary data."""

    def __init__(self, code: str, location: tuple[str | int, ...], message: str):
        self.code = code
        self.location = location
        super().__init__(message)


def ensure_supported_schema_version(version: object) -> int:
    """Validate a schema version before dispatching a boundary payload."""

    if isinstance(version, bool) or not isinstance(version, int):
        raise IncompatibleSchemaVersionError(version)
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise IncompatibleSchemaVersionError(version)
    return version


def is_schema_version_compatible(version: object) -> bool:
    """Return whether a version is accepted without performing dispatch."""

    try:
        ensure_supported_schema_version(version)
    except IncompatibleSchemaVersionError:
        return False
    return True


def _json_value(value: Any) -> Any:
    """Return a deterministic JSON-compatible representation."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(_json_value(item) for item in value)
    return value


def canonical_json(value: Any) -> str:
    """Serialize a value for stable identity and audit hashing."""

    return json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def stable_digest(value: Any) -> str:
    """Return a SHA-256 digest over the canonical representation of ``value``."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class BoundaryModel(BaseModel):
    """Base class for all E1 serialized contracts."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        populate_by_name=True,
        validate_assignment=True,
    )

    schema_version: SchemaVersion = CURRENT_SCHEMA_VERSION
    CURRENT_SCHEMA_VERSION: ClassVar[int] = CURRENT_SCHEMA_VERSION

    @model_validator(mode="before")
    @classmethod
    def _validate_version(cls, value: Any) -> Any:
        if isinstance(value, Mapping) and "schema_version" in value:
            ensure_supported_schema_version(value["schema_version"])
        return value

    @classmethod
    def model_validate_boundary(cls, value: Any) -> Any:
        """Validate a Python value and map version errors to a stable error."""

        if isinstance(value, Mapping):
            if "schema_version" not in value:
                raise BoundaryValidationError(
                    "input.required",
                    ("schema_version",),
                    "input.required at schema_version",
                )
            ensure_supported_schema_version(value["schema_version"])
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            first = exc.errors()[0]
            error_type = str(first.get("type", ""))
            if error_type == "extra_forbidden":
                code = "input.unknown_field"
            elif error_type == "missing":
                code = "input.required"
            elif error_type.startswith(("int_", "string_", "bool_", "datetime_")):
                code = "input.type"
            else:
                code = "input.invalid"
            location = tuple(first.get("loc", ()))
            raise BoundaryValidationError(
                code,
                location,
                f"{code} at {'.'.join(str(part) for part in location)}",
            ) from exc

    @classmethod
    def model_validate_json_boundary(cls, value: str | bytes) -> Any:
        """Validate a JSON boundary payload with the same version policy."""

        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise BoundaryValidationError("input.invalid", (), "Invalid JSON") from exc
        return cls.model_validate_boundary(parsed)


class VersionEnvelope(BoundaryModel):
    """Generic closed envelope used when a payload type is transported by name."""

    payload_type: str
    payload: dict[str, Any]


VersionedEnvelope = VersionEnvelope


def validate_boundary_model[ModelT: BoundaryModel](
    model: type[ModelT], value: Any
) -> ModelT:
    """Validate a model at a trust boundary using the shared policy."""

    return model.model_validate_boundary(value)
