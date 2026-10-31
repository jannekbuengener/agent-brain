"""Typed failure modes for the Improvement Observation write boundary."""

from __future__ import annotations


class ImprovementStoreError(Exception):
    """Base error for Improvement Observation Store operations."""


class ImprovementStoreUnavailable(ImprovementStoreError):
    """Backend temporarily or permanently unavailable."""


class ImprovementValidationError(ImprovementStoreError):
    """Observation or query rejected for contract/schema reasons."""


class InvalidImprovementScope(ImprovementValidationError):
    """Skill/repository/improvement scope is invalid or inconsistent."""


class ImprovementIdentityAmbiguous(ImprovementValidationError):
    """Root-cause identity cannot be determined without guessing."""
