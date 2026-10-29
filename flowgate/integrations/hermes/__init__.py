"""Hermes Agent integration for FlowGate.

This package provides a dependency-free router that Hermes can call before
spawning ``delegate_task`` child agents. FlowGate recommends provider,
model, and reasoning-effort targets; Hermes remains responsible for
credentials, base URLs, fallback chains, and child-agent construction.
"""

from .classifier import HermesTaskClassification, HermesTaskClassifier
from .config import HermesRouteProfile, HermesRoutingConfig
from .router import HermesDelegationRouter
from .skill_metadata import (
    extract_flowgate_skill_metadata,
    profile_from_skill_metadata,
)
from .types import HermesDelegationDecision, HermesDelegationRequest

__all__ = [
    "HermesDelegationDecision",
    "HermesDelegationRequest",
    "HermesDelegationRouter",
    "HermesRouteProfile",
    "HermesRoutingConfig",
    "HermesTaskClassification",
    "HermesTaskClassifier",
    "extract_flowgate_skill_metadata",
    "profile_from_skill_metadata",
]
