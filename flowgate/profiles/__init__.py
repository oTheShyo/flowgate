"""
User Profile System for flowgate.

This module provides a comprehensive user profile system for managing
thousands of users with different subscription tiers, limits, and preferences.

Key components:
- TierConfig: Predefined subscription tiers (FREE, STARTER, PRO, BUSINESS, ENTERPRISE)
- UserProfile: Multi-dimensional user profile (identity, tier, limits, preferences, guardrails, telemetry)
- UserProfileManager: Profile management at scale with caching and database integration

Example usage:
    from flowgate.profiles import UserProfile, TierLevel
    from flowgate import CascadeAgent

    # Create profile from tier preset
    profile = UserProfile.from_tier(TierLevel.PRO, user_id="user_123")

    # Create agent from profile
    agent = CascadeAgent.from_profile(profile)

    # Use profile manager for scaling
    from flowgate.profiles import UserProfileManager

    manager = UserProfileManager(cache_ttl_seconds=300)
    profile = await manager.get_profile("user_123")
"""

from .tier_config import TierConfig, TierLevel, TIER_PRESETS
from .user_profile import UserProfile
from .profile_manager import UserProfileManager

__all__ = [
    # Tier system
    "TierConfig",
    "TierLevel",
    "TIER_PRESETS",
    # User profiles
    "UserProfile",
    # Profile management
    "UserProfileManager",
]
