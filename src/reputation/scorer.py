"""
Session Scorer
Pure function for computing IP reputation scores from session signals.

This module implements deterministic scoring logic with no side effects.
All inputs → outputs are fully traceable and auditable.
"""

from dataclasses import dataclass

from ..core.constants import (
    SCORE_ABNORMAL_TERMINATION,
    SCORE_BLOCK_DETECTED,
    SCORE_CAPTCHA_DETECTED,
    SCORE_NORMAL_NAVIGATION,
    SCORE_REALISTIC_DURATION,
    SCORE_SUCCESSFUL_COMPLETION,
    TIER_BAD_THRESHOLD,
    TIER_GOOD_THRESHOLD,
    ReputationTier,
    SessionSignal,
)
from ..session.runner import SessionResult


@dataclass
class ScoringResult:
    """
    Result of scoring a session.

    Contains the computed score, tier, and breakdown of how score was calculated.
    """

    score: int
    tier: ReputationTier
    positive_signals: list[str]
    negative_signals: list[str]
    score_breakdown: dict

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "tier": self.tier.value,
            "positive_signals": self.positive_signals,
            "negative_signals": self.negative_signals,
            "score_breakdown": self.score_breakdown,
        }


# Signal to score mapping
SIGNAL_SCORES = {
    # Positive signals
    SessionSignal.SUCCESSFUL_COMPLETION.value: SCORE_SUCCESSFUL_COMPLETION,
    SessionSignal.REALISTIC_DURATION.value: SCORE_REALISTIC_DURATION,
    SessionSignal.NORMAL_NAVIGATION.value: SCORE_NORMAL_NAVIGATION,
    # Negative signals
    SessionSignal.CAPTCHA_DETECTED.value: SCORE_CAPTCHA_DETECTED,
    SessionSignal.BLOCK_DETECTED.value: SCORE_BLOCK_DETECTED,
    SessionSignal.ABNORMAL_TERMINATION.value: SCORE_ABNORMAL_TERMINATION,
    # Neutral signals (no score impact)
    SessionSignal.TIMEOUT.value: 0,
    SessionSignal.ERROR.value: 0,  # Error without abnormal termination
}


class SessionScorer:
    """
    Scores sessions based on outcome signals.

    This is a pure function class - no state, no side effects.
    Given the same input, always produces the same output.

    Scoring Logic:
        Positive signals add points:
        +2  successful_completion - Completed without errors
        +1  realistic_duration   - Duration within expected range
        +1  normal_navigation    - No suspicious patterns

        Negative signals subtract points:
        -2  captcha_detected     - Captcha challenge triggered
        -3  block_detected       - IP/account block detected
        -2  abnormal_termination - Crash or unexpected end

    Tier Determination:
        score <= -2  → BAD       (destroy immediately)
        score -1 to +1 → NEUTRAL (destroy or cooldown)
        score >= +2  → GOOD      (may reuse)

    Usage:
        scorer = SessionScorer()
        result = scorer.score(session_result)
        print(f"Score: {result.score}, Tier: {result.tier}")

    Or use static method directly:
        result = SessionScorer.score_signals(["successful_completion", "realistic_duration"])
    """

    @staticmethod
    def score(session_result: SessionResult) -> ScoringResult:
        """
        Score a session result.

        Args:
            session_result: SessionResult from BotSessionRunner

        Returns:
            ScoringResult with score, tier, and breakdown
        """
        return SessionScorer.score_signals(session_result.signals)

    @staticmethod
    def score_signals(signals: list[str]) -> ScoringResult:
        """
        Score a list of signal strings.

        This is the core scoring function - pure, deterministic, no side effects.

        Args:
            signals: List of signal strings (e.g., ["successful_completion", "realistic_duration"])

        Returns:
            ScoringResult with computed score and tier
        """
        total_score = 0
        positive_signals = []
        negative_signals = []
        score_breakdown = {}

        # Calculate score from signals
        for signal in signals:
            if signal in SIGNAL_SCORES:
                signal_score = SIGNAL_SCORES[signal]
                total_score += signal_score
                score_breakdown[signal] = signal_score

                if signal_score > 0:
                    positive_signals.append(signal)
                elif signal_score < 0:
                    negative_signals.append(signal)

        # Determine tier
        tier = SessionScorer._compute_tier(total_score)

        return ScoringResult(
            score=total_score,
            tier=tier,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            score_breakdown=score_breakdown,
        )

    @staticmethod
    def _compute_tier(score: int) -> ReputationTier:
        """
        Compute reputation tier from score.

        Tier logic:
            score <= -2  → BAD
            score -1 to +1 → NEUTRAL
            score >= +2  → GOOD

        Args:
            score: Total session score

        Returns:
            ReputationTier enum value
        """
        if score <= TIER_BAD_THRESHOLD:
            return ReputationTier.BAD
        elif score >= TIER_GOOD_THRESHOLD:
            return ReputationTier.GOOD
        else:
            return ReputationTier.NEUTRAL

    @staticmethod
    def get_max_possible_score() -> int:
        """Get the maximum possible score (all positive signals)"""
        return SCORE_SUCCESSFUL_COMPLETION + SCORE_REALISTIC_DURATION + SCORE_NORMAL_NAVIGATION

    @staticmethod
    def get_min_possible_score() -> int:
        """Get the minimum possible score (all negative signals)"""
        return SCORE_CAPTCHA_DETECTED + SCORE_BLOCK_DETECTED + SCORE_ABNORMAL_TERMINATION

    @staticmethod
    def explain_score(scoring_result: ScoringResult) -> str:
        """
        Generate a human-readable explanation of a score.

        Args:
            scoring_result: ScoringResult to explain

        Returns:
            Human-readable explanation string
        """
        lines = []
        lines.append(f"Score: {scoring_result.score} → Tier: {scoring_result.tier.value}")
        lines.append("")

        if scoring_result.positive_signals:
            lines.append("Positive signals:")
            for signal in scoring_result.positive_signals:
                score = scoring_result.score_breakdown.get(signal, 0)
                lines.append(f"  +{score}: {signal}")

        if scoring_result.negative_signals:
            lines.append("Negative signals:")
            for signal in scoring_result.negative_signals:
                score = scoring_result.score_breakdown.get(signal, 0)
                lines.append(f"  {score}: {signal}")

        lines.append("")
        lines.append(f"Thresholds: BAD <= {TIER_BAD_THRESHOLD}, GOOD >= {TIER_GOOD_THRESHOLD}")

        return "\n".join(lines)
