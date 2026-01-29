"""
Proxy Rotation Engine
Implements weighted, data-driven proxy selection based on performance metrics.

Provides:
- Weighted random selection based on proxy scores
- Score calculation from success rate, latency, and failure history
- Integration with ProxyStatsManager for metrics
"""

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from loguru import logger

from .stats import ProxyStats, ProxyStatsManager


@dataclass
class RotationConfig:
    """
    Configuration for proxy rotation scoring.
    
    Weights determine how much each factor influences the proxy score.
    Higher score = more likely to be selected.
    """
    # Weight for success rate (0-100) contribution
    weight_success: float = 1.0
    
    # Weight for latency penalty (normalized to 0-1)
    weight_latency: float = 0.2
    
    # Weight for consecutive failure penalty
    weight_failure: float = 0.3
    
    # Maximum latency for normalization (ms)
    max_latency_ms: int = 5000
    
    # Minimum score to be considered for selection
    min_score: float = 10.0
    
    # Bonus for proxies with many successful uses
    experience_bonus: float = 0.1
    
    # Experience threshold (number of uses)
    experience_threshold: int = 10


class ProxyRotationEngine:
    """
    Weighted proxy rotation based on performance metrics.
    
    Selection Algorithm:
    1. Get available proxies for country (not disabled, not in cooldown)
    2. Calculate score for each proxy
    3. Use weighted random selection based on scores
    
    Score Formula:
        base_score = success_rate * weight_success
        latency_penalty = (avg_latency / max_latency) * weight_latency * 100
        failure_penalty = consecutive_failures * weight_failure * 10
        experience_bonus = (uses > threshold) ? experience_bonus * 10 : 0
        
        final_score = base_score - latency_penalty - failure_penalty + experience_bonus
        final_score = max(final_score, min_score if eligible else 0)
    
    Usage:
        engine = ProxyRotationEngine(stats_manager)
        
        # Select best proxy
        proxy_id = engine.select_proxy(country="US")
        
        # Get proxy with score
        proxy_id, score = engine.select_proxy_with_score(country="US")
    """
    
    def __init__(
        self,
        stats_manager: ProxyStatsManager,
        config: Optional[RotationConfig] = None
    ):
        """
        Initialize rotation engine.
        
        Args:
            stats_manager: ProxyStatsManager for metrics
            config: Optional rotation configuration
        """
        self.stats_manager = stats_manager
        self.config = config or RotationConfig()
        
        logger.info("ProxyRotationEngine initialized")
    
    def calculate_score(self, stats: ProxyStats) -> float:
        """
        Calculate rotation score for a proxy.
        
        Higher score = better proxy = more likely to be selected.
        
        Args:
            stats: Proxy statistics
            
        Returns:
            Score (0-100+ range, higher is better)
        """
        # Base score from success rate (0-100)
        base_score = stats.success_rate * self.config.weight_success
        
        # Latency penalty (normalized 0-1, then scaled)
        latency_normalized = min(stats.avg_latency_ms / self.config.max_latency_ms, 1.0)
        latency_penalty = latency_normalized * self.config.weight_latency * 100
        
        # Consecutive failure penalty
        failure_penalty = stats.consecutive_failures * self.config.weight_failure * 10
        
        # Experience bonus for well-tested proxies
        experience_bonus = 0.0
        if stats.total_count >= self.config.experience_threshold:
            experience_bonus = self.config.experience_bonus * 10
        
        # Calculate final score
        score = base_score - latency_penalty - failure_penalty + experience_bonus
        
        # Ensure minimum score for eligible proxies
        if stats.is_available and score < self.config.min_score:
            score = self.config.min_score
        
        return max(score, 0)
    
    def get_scored_proxies(
        self,
        country: Optional[str] = None
    ) -> List[Tuple[ProxyStats, float]]:
        """
        Get all available proxies with their scores.
        
        Args:
            country: Optional filter by country
            
        Returns:
            List of (ProxyStats, score) tuples, sorted by score descending
        """
        # Check and re-enable cooled-down proxies
        self.stats_manager.check_and_reenable_cooled_down()
        
        # Get available proxies
        available = self.stats_manager.get_available_proxies(country)
        
        # Calculate scores
        scored = [(stats, self.calculate_score(stats)) for stats in available]
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
    
    def select_proxy(self, country: Optional[str] = None) -> Optional[str]:
        """
        Select a proxy using weighted random selection.
        
        Args:
            country: Optional filter by country
            
        Returns:
            Selected proxy_id or None if no proxies available
        """
        result = self.select_proxy_with_score(country)
        return result[0] if result else None
    
    def select_proxy_with_score(
        self,
        country: Optional[str] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Select a proxy with its score.
        
        Args:
            country: Optional filter by country
            
        Returns:
            Tuple of (proxy_id, score) or None if no proxies available
        """
        scored = self.get_scored_proxies(country)
        
        if not scored:
            logger.warning(f"No available proxies for country: {country}")
            return None
        
        # Extract scores for weighted selection
        scores = [max(score, 0.1) for _, score in scored]  # Minimum weight of 0.1
        
        # Weighted random selection
        selected = random.choices(scored, weights=scores, k=1)[0]
        stats, score = selected
        
        logger.debug(f"Selected proxy {stats.proxy_id} (score: {score:.2f})")
        return (stats.proxy_id, score)
    
    def select_best_proxy(self, country: Optional[str] = None) -> Optional[str]:
        """
        Select the best proxy by score (no randomization).
        
        Args:
            country: Optional filter by country
            
        Returns:
            Best proxy_id or None if no proxies available
        """
        scored = self.get_scored_proxies(country)
        
        if not scored:
            logger.warning(f"No available proxies for country: {country}")
            return None
        
        best = scored[0]
        logger.debug(f"Selected best proxy {best[0].proxy_id} (score: {best[1]:.2f})")
        return best[0].proxy_id
    
    def get_proxy_ranking(
        self,
        country: Optional[str] = None,
        limit: int = 10
    ) -> List[dict]:
        """
        Get proxy ranking for display/dashboard.
        
        Args:
            country: Optional filter by country
            limit: Maximum number of results
            
        Returns:
            List of proxy info dicts with scores
        """
        scored = self.get_scored_proxies(country)[:limit]
        
        return [
            {
                "proxy_id": stats.proxy_id,
                "country": stats.country,
                "score": round(score, 2),
                "success_rate": round(stats.success_rate, 2),
                "avg_latency_ms": round(stats.avg_latency_ms, 2),
                "total_uses": stats.total_count,
                "consecutive_failures": stats.consecutive_failures,
                "is_available": stats.is_available
            }
            for stats, score in scored
        ]
    
    def explain_score(self, proxy_id: str) -> Optional[dict]:
        """
        Explain the score calculation for a proxy.
        
        Args:
            proxy_id: Proxy identifier
            
        Returns:
            Dict with score breakdown or None if proxy not found
        """
        stats = self.stats_manager.get_stats(proxy_id)
        
        if not stats:
            return None
        
        # Calculate components
        base_score = stats.success_rate * self.config.weight_success
        latency_normalized = min(stats.avg_latency_ms / self.config.max_latency_ms, 1.0)
        latency_penalty = latency_normalized * self.config.weight_latency * 100
        failure_penalty = stats.consecutive_failures * self.config.weight_failure * 10
        
        experience_bonus = 0.0
        if stats.total_count >= self.config.experience_threshold:
            experience_bonus = self.config.experience_bonus * 10
        
        final_score = self.calculate_score(stats)
        
        return {
            "proxy_id": proxy_id,
            "country": stats.country,
            "is_available": stats.is_available,
            "is_disabled": stats.is_disabled,
            "is_in_cooldown": stats.is_in_cooldown,
            "score_breakdown": {
                "base_score": round(base_score, 2),
                "latency_penalty": round(-latency_penalty, 2),
                "failure_penalty": round(-failure_penalty, 2),
                "experience_bonus": round(experience_bonus, 2),
                "final_score": round(final_score, 2)
            },
            "stats": {
                "success_rate": round(stats.success_rate, 2),
                "avg_latency_ms": round(stats.avg_latency_ms, 2),
                "consecutive_failures": stats.consecutive_failures,
                "total_uses": stats.total_count
            },
            "config": {
                "weight_success": self.config.weight_success,
                "weight_latency": self.config.weight_latency,
                "weight_failure": self.config.weight_failure,
                "max_latency_ms": self.config.max_latency_ms,
                "min_score": self.config.min_score
            }
        }
