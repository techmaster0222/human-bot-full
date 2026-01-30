"""
Profile Reuse Policy
Explicit decision logic for profile reuse after session completion.

All decisions are logged with clear reasons. No hidden heuristics.
"""

from dataclasses import dataclass

from loguru import logger

from ..core.constants import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_MAX_REUSE_COUNT,
    ReputationTier,
    ReuseDecision,
)
from .cooldown import CooldownManager
from .store import ReputationStore


@dataclass
class ReuseConfig:
    """Configuration for reuse policy"""

    max_reuse_count: int = DEFAULT_MAX_REUSE_COUNT
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS
    allow_neutral_reuse: bool = False  # If True, NEUTRAL can be reused after cooldown
    require_same_country: bool = True  # Reuse only with same country
    require_same_vps: bool = True  # Reuse only on same VPS


@dataclass
class PolicyDecision:
    """
    A reuse policy decision.

    Contains the decision and a human-readable reason.
    """

    action: ReuseDecision
    reason: str
    profile_id: str
    tier: ReputationTier
    reuse_count: int

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "profile_id": self.profile_id,
            "tier": self.tier.value,
            "reuse_count": self.reuse_count,
        }


class ProfileReusePolicy:
    """
    Determines whether a profile should be destroyed, put in cooldown, or reused.

    Core Rules:
    - BAD tier → DESTROY immediately, never reuse
    - NEUTRAL tier → DESTROY by default (or COOLDOWN if allow_neutral_reuse)
    - GOOD tier → REUSE if:
        - reuse_count < max_reuse_count
        - same country (if require_same_country)
        - same VPS (if require_same_vps)
        - not in cooldown

    All decisions are explicit and logged with reasons.
    No hidden logic or silent defaults.

    Usage:
        policy = ProfileReusePolicy(config, store, cooldown_manager)

        decision = policy.decide(profile_id, tier, country, vps_id)

        print(f"Decision: {decision.action.value}")
        print(f"Reason: {decision.reason}")
    """

    def __init__(
        self, config: ReuseConfig, store: ReputationStore, cooldown_manager: CooldownManager
    ):
        """
        Initialize policy.

        Args:
            config: Reuse configuration
            store: Reputation store for history queries
            cooldown_manager: Cooldown manager for time-based gates
        """
        self.config = config
        self.store = store
        self.cooldown = cooldown_manager

        logger.info(
            f"ProfileReusePolicy initialized "
            f"(max_reuse: {config.max_reuse_count}, "
            f"cooldown: {config.cooldown_seconds}s)"
        )

    def decide(
        self,
        profile_id: str,
        tier: ReputationTier,
        country: str | None = None,
        vps_id: str | None = None,
        original_country: str | None = None,
        original_vps_id: str | None = None,
    ) -> PolicyDecision:
        """
        Make a reuse decision for a profile.

        Args:
            profile_id: AdsPower profile ID
            tier: Computed reputation tier
            country: Country for potential reuse
            vps_id: VPS for potential reuse
            original_country: Original country profile was created with
            original_vps_id: Original VPS profile was created on

        Returns:
            PolicyDecision with action and reason
        """
        reuse_count = self.store.get_reuse_count(profile_id)

        # Rule 1: BAD tier → DESTROY immediately
        if tier == ReputationTier.BAD:
            return PolicyDecision(
                action=ReuseDecision.DESTROY,
                reason="Tier is BAD - profile must be destroyed immediately",
                profile_id=profile_id,
                tier=tier,
                reuse_count=reuse_count,
            )

        # Rule 2: NEUTRAL tier → DESTROY or COOLDOWN
        if tier == ReputationTier.NEUTRAL:
            if self.config.allow_neutral_reuse:
                # Put in cooldown instead of destroying
                self.cooldown.start_cooldown(
                    profile_id,
                    self.config.cooldown_seconds,
                    reason="NEUTRAL tier - cooldown before potential reuse",
                )
                return PolicyDecision(
                    action=ReuseDecision.COOLDOWN,
                    reason=f"Tier is NEUTRAL - cooldown for {self.config.cooldown_seconds}s",
                    profile_id=profile_id,
                    tier=tier,
                    reuse_count=reuse_count,
                )
            else:
                return PolicyDecision(
                    action=ReuseDecision.DESTROY,
                    reason="Tier is NEUTRAL - destroying (allow_neutral_reuse=False)",
                    profile_id=profile_id,
                    tier=tier,
                    reuse_count=reuse_count,
                )

        # Rule 3: GOOD tier → check reuse conditions

        # Check reuse count
        if reuse_count >= self.config.max_reuse_count:
            return PolicyDecision(
                action=ReuseDecision.DESTROY,
                reason=f"Reuse count {reuse_count} >= max {self.config.max_reuse_count}",
                profile_id=profile_id,
                tier=tier,
                reuse_count=reuse_count,
            )

        # Check cooldown
        if self.cooldown.is_in_cooldown(profile_id):
            remaining = self.cooldown.get_remaining(profile_id)
            return PolicyDecision(
                action=ReuseDecision.COOLDOWN,
                reason=f"Profile in cooldown - {remaining:.0f}s remaining",
                profile_id=profile_id,
                tier=tier,
                reuse_count=reuse_count,
            )

        # Check country match
        if self.config.require_same_country and original_country and country:
            if original_country != country:
                return PolicyDecision(
                    action=ReuseDecision.DESTROY,
                    reason=f"Country mismatch: original={original_country}, requested={country}",
                    profile_id=profile_id,
                    tier=tier,
                    reuse_count=reuse_count,
                )

        # Check VPS match
        if self.config.require_same_vps and original_vps_id and vps_id:
            if original_vps_id != vps_id:
                return PolicyDecision(
                    action=ReuseDecision.DESTROY,
                    reason=f"VPS mismatch: original={original_vps_id}, requested={vps_id}",
                    profile_id=profile_id,
                    tier=tier,
                    reuse_count=reuse_count,
                )

        # All checks passed → REUSE
        return PolicyDecision(
            action=ReuseDecision.REUSE,
            reason=f"GOOD tier, reuse_count {reuse_count} < max {self.config.max_reuse_count}",
            profile_id=profile_id,
            tier=tier,
            reuse_count=reuse_count,
        )

    def should_destroy(self, decision: PolicyDecision) -> bool:
        """Check if decision is to destroy"""
        return decision.action == ReuseDecision.DESTROY

    def should_reuse(self, decision: PolicyDecision) -> bool:
        """Check if decision is to reuse"""
        return decision.action == ReuseDecision.REUSE

    def should_cooldown(self, decision: PolicyDecision) -> bool:
        """Check if decision is to cooldown"""
        return decision.action == ReuseDecision.COOLDOWN

    def get_reuse_count(self, profile_id: str) -> int:
        """Get current reuse count for a profile"""
        return self.store.get_reuse_count(profile_id)

    def can_reuse_now(
        self, profile_id: str, country: str | None = None, vps_id: str | None = None
    ) -> bool:
        """
        Quick check if a profile can be reused right now.

        This is a convenience method that checks the last known tier
        and applies policy rules.

        Args:
            profile_id: Profile to check
            country: Country for reuse
            vps_id: VPS for reuse

        Returns:
            True if profile can be reused immediately
        """
        # Get last record
        record = self.store.get_latest_for_profile(profile_id)
        if not record:
            return False

        # Parse tier
        try:
            tier = ReputationTier(record.tier)
        except ValueError:
            return False

        # Make decision
        decision = self.decide(
            profile_id=profile_id,
            tier=tier,
            country=country,
            vps_id=vps_id,
            original_country=record.country,
            original_vps_id=record.vps_id,
        )

        return decision.action == ReuseDecision.REUSE
