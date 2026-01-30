"""
Proxy Module Tests
==================
Comprehensive tests for proxy management, rotation, and statistics.
"""

from datetime import datetime, timedelta

import pytest
from src.proxy import IPRoyalProxy, ProxyConfig, ProxySession

# ============== ProxyConfig Tests ==============


@pytest.mark.proxy
@pytest.mark.unit
class TestProxyConfig:
    """ProxyConfig dataclass tests."""

    def test_basic_creation(self):
        """Should create config with required fields."""
        config = ProxyConfig(
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass",
        )

        assert config.host == "proxy.example.com"
        assert config.port == 8080
        assert config.username == "user"
        assert config.password == "pass"

    def test_creation_with_country(self):
        """Should create config with optional country."""
        config = ProxyConfig(
            host="proxy.com",
            port=8080,
            username="u",
            password="p",
            country="US",
        )

        assert config.country == "US"

    def test_url_generation_with_auth(self):
        """Should generate URL with authentication."""
        config = ProxyConfig(
            host="proxy.com",
            port=8080,
            username="myuser",
            password="mypass",
        )

        url = config.url
        assert "myuser:mypass" in url
        assert "proxy.com:8080" in url
        assert url.startswith("http://")

    def test_url_no_auth(self):
        """Should generate URL without authentication."""
        config = ProxyConfig(
            host="proxy.com",
            port=8080,
            username="user",
            password="pass",
        )

        url_no_auth = config.url_no_auth
        assert "user" not in url_no_auth
        assert "pass" not in url_no_auth
        assert "proxy.com:8080" in url_no_auth

    def test_to_adspower_config(self):
        """Should convert to AdsPower format."""
        config = ProxyConfig(
            host="proxy.com",
            port=8080,
            username="user",
            password="pass",
        )

        ads_config = config.to_adspower_config()

        assert ads_config["proxy_host"] == "proxy.com"
        assert ads_config["proxy_port"] == "8080"
        assert ads_config["proxy_user"] == "user"
        assert ads_config["proxy_password"] == "pass"

    def test_different_ports(self):
        """Should handle various port numbers."""
        ports = [80, 443, 8080, 12321, 3128, 1080]

        for port in ports:
            config = ProxyConfig(host="proxy.com", port=port, username="u", password="p")
            assert config.port == port
            assert str(port) in config.url


# ============== ProxySession Tests ==============


@pytest.mark.proxy
@pytest.mark.unit
class TestProxySession:
    """ProxySession management tests."""

    @pytest.fixture
    def base_config(self) -> ProxyConfig:
        """Return base proxy config for session tests."""
        return ProxyConfig(
            host="proxy.com",
            port=8080,
            username="user",
            password="pass",
        )

    def test_session_creation(self, base_config: ProxyConfig):
        """Should create session with correct attributes."""
        now = datetime.now()
        expires = now + timedelta(minutes=10)

        session = ProxySession(
            config=base_config,
            session_id="sess_12345",
            started_at=now,
            expires_at=expires,
        )

        assert session.session_id == "sess_12345"
        assert session.config == base_config
        assert session.started_at == now
        assert session.expires_at == expires

    def test_session_not_expired(self, base_config: ProxyConfig):
        """Should correctly identify non-expired session."""
        now = datetime.now()
        session = ProxySession(
            config=base_config,
            session_id="active",
            started_at=now,
            expires_at=now + timedelta(minutes=10),
        )

        assert not session.is_expired

    def test_session_expired(self, base_config: ProxyConfig):
        """Should correctly identify expired session."""
        past = datetime.now() - timedelta(minutes=20)
        session = ProxySession(
            config=base_config,
            session_id="expired",
            started_at=past - timedelta(minutes=10),
            expires_at=past,
        )

        assert session.is_expired

    def test_session_just_expired(self, base_config: ProxyConfig):
        """Should handle session that just expired."""
        now = datetime.now()
        session = ProxySession(
            config=base_config,
            session_id="just_expired",
            started_at=now - timedelta(seconds=1),
            expires_at=now - timedelta(milliseconds=1),
        )

        assert session.is_expired

    def test_session_time_remaining(self, base_config: ProxyConfig):
        """Session should track remaining time correctly."""
        now = datetime.now()
        duration = timedelta(minutes=10)

        session = ProxySession(
            config=base_config,
            session_id="timed",
            started_at=now,
            expires_at=now + duration,
        )

        remaining = session.expires_at - datetime.now()
        assert remaining.total_seconds() > 0
        assert remaining.total_seconds() <= duration.total_seconds()


# ============== IPRoyalProxy Tests ==============


@pytest.mark.proxy
@pytest.mark.unit
class TestIPRoyalProxy:
    """IPRoyal proxy provider tests."""

    def test_creation_with_credentials(self):
        """Should create proxy with credentials."""
        proxy = IPRoyalProxy(
            username="test_user",
            password="test_pass",
        )

        assert proxy.username == "test_user"
        assert proxy.password == "test_pass"

    def test_default_host_and_port(self):
        """Should use IPRoyal default host and port."""
        proxy = IPRoyalProxy(username="u", password="p")

        assert proxy.host == "geo.iproyal.com"
        assert proxy.port == 12321

    def test_custom_host_and_port(self):
        """Should accept custom host and port."""
        proxy = IPRoyalProxy(
            username="u",
            password="p",
            host="custom.proxy.com",
            port=9999,
        )

        assert proxy.host == "custom.proxy.com"
        assert proxy.port == 9999

    def test_get_rotating_proxy(self):
        """Should return rotating proxy config."""
        proxy = IPRoyalProxy(username="user", password="pass")

        config = proxy.get_rotating_proxy(country="US")

        assert isinstance(config, ProxyConfig)
        assert config.country == "US"
        assert config.host == "geo.iproyal.com"

    def test_get_sticky_proxy(self):
        """Should return sticky proxy with session ID."""
        proxy = IPRoyalProxy(username="user", password="pass")

        config, session_id = proxy.get_sticky_proxy(country="US")

        assert isinstance(config, ProxyConfig)
        assert session_id is not None
        assert len(session_id) > 0

    def test_sticky_proxy_duration(self):
        """Should accept duration parameter."""
        proxy = IPRoyalProxy(username="user", password="pass")

        config, session_id = proxy.get_sticky_proxy(country="UK", duration=600)

        assert config.country == "UK"
        assert session_id is not None

    @pytest.mark.parametrize("country", ["US", "UK", "DE", "FR", "JP", "CA", "AU"])
    def test_different_countries(self, country: str):
        """Should support various countries."""
        proxy = IPRoyalProxy(username="u", password="p")

        config, session_id = proxy.get_sticky_proxy(country=country)

        assert config.country == country

    def test_unique_session_ids(self):
        """Should generate unique session IDs."""
        proxy = IPRoyalProxy(username="u", password="p")

        session_ids = set()
        for _ in range(100):
            _, session_id = proxy.get_sticky_proxy(country="US")
            session_ids.add(session_id)

        # All should be unique
        assert len(session_ids) == 100

    def test_proxy_url_format(self):
        """Should generate correct proxy URL format."""
        proxy = IPRoyalProxy(username="myuser", password="mypass")

        config = proxy.get_rotating_proxy(country="US")
        url = config.url

        assert "myuser" in url
        assert "mypass" in url
        assert "geo.iproyal.com" in url


# ============== Proxy Stats Tests ==============


@pytest.mark.proxy
@pytest.mark.unit
class TestProxyStatsManager:
    """Proxy statistics manager tests."""

    @pytest.fixture
    def stats_manager(self, temp_db: str):
        """Create stats manager with temp database."""
        from src.proxy.stats import ProxyStatsManager

        return ProxyStatsManager(db_path=temp_db)

    def test_record_success(self, stats_manager):
        """Should record successful proxy use."""
        stats_manager.record_success(
            proxy_id="test_proxy_1",
            country="US",
            latency_ms=150,
        )

        stats = stats_manager.get_stats("test_proxy_1")
        assert stats.success_count == 1
        assert stats.failure_count == 0

    def test_record_failure(self, stats_manager):
        """Should record failed proxy use."""
        stats_manager.record_failure(
            proxy_id="test_proxy_2",
            country="US",
            error="Connection timeout",
        )

        stats = stats_manager.get_stats("test_proxy_2")
        assert stats.failure_count == 1

    def test_success_rate_calculation(self, stats_manager):
        """Should calculate correct success rate."""
        proxy_id = "rate_test_proxy"

        # 8 successes, 2 failures = 80% success rate
        for _ in range(8):
            stats_manager.record_success(proxy_id, country="US")
        for _ in range(2):
            stats_manager.record_failure(proxy_id, country="US")

        stats = stats_manager.get_stats(proxy_id)
        assert stats.success_rate == pytest.approx(80.0, abs=1)

    def test_zero_division_handling(self, stats_manager):
        """Should handle zero total requests."""
        stats = stats_manager.get_stats("nonexistent_proxy")

        # Should return 0 or handle gracefully
        assert stats is None or stats.success_rate >= 0

    def test_multiple_proxies(self, stats_manager):
        """Should track multiple proxies independently."""
        stats_manager.record_success("proxy_a", country="US")
        stats_manager.record_success("proxy_a", country="US")
        stats_manager.record_success("proxy_b", country="UK")
        stats_manager.record_failure("proxy_b", country="UK")

        stats_a = stats_manager.get_stats("proxy_a")
        stats_b = stats_manager.get_stats("proxy_b")

        assert stats_a.success_count == 2
        assert stats_b.success_count == 1
        assert stats_b.failure_count == 1

    def test_get_all_stats(self, stats_manager):
        """Should return all proxy statistics."""
        # Add some data
        stats_manager.record_success("proxy_1", country="US")
        stats_manager.record_success("proxy_2", country="UK")
        stats_manager.record_success("proxy_3", country="DE")

        all_stats = stats_manager.get_all_stats()

        assert len(all_stats) >= 3

    def test_latency_tracking(self, stats_manager):
        """Should track latency correctly."""
        proxy_id = "latency_test"

        stats_manager.record_success(proxy_id, country="US", latency_ms=100)
        stats_manager.record_success(proxy_id, country="US", latency_ms=200)
        stats_manager.record_success(proxy_id, country="US", latency_ms=150)

        stats = stats_manager.get_stats(proxy_id)
        # Average should be around 150
        assert stats.avg_latency_ms == pytest.approx(150, abs=10)


# ============== Integration Tests ==============


@pytest.mark.proxy
@pytest.mark.integration
class TestProxyIntegration:
    """Proxy system integration tests."""

    def test_full_proxy_lifecycle(self, temp_db: str):
        """Test complete proxy usage lifecycle."""
        from src.proxy import IPRoyalProxy
        from src.proxy.stats import ProxyStatsManager

        # Setup
        proxy_provider = IPRoyalProxy(username="test", password="test")
        stats_manager = ProxyStatsManager(db_path=temp_db)

        # Get proxy
        config, session_id = proxy_provider.get_sticky_proxy(country="US", duration=300)

        # Simulate usage
        proxy_id = f"{config.host}:{config.port}"

        # Record some activity
        stats_manager.record_success(proxy_id, country="US", latency_ms=120)
        stats_manager.record_success(proxy_id, country="US", latency_ms=130)
        stats_manager.record_failure(proxy_id, country="US", error="Timeout")

        # Verify stats
        stats = stats_manager.get_stats(proxy_id)
        assert stats.success_count == 2
        assert stats.failure_count == 1
        assert stats.success_rate == pytest.approx(66.67, abs=1)

    def test_proxy_rotation_simulation(self, temp_db: str):
        """Simulate proxy rotation with multiple proxies."""
        from src.proxy import IPRoyalProxy
        from src.proxy.stats import ProxyStatsManager

        proxy_provider = IPRoyalProxy(username="test", password="test")
        stats_manager = ProxyStatsManager(db_path=temp_db)

        countries = ["US", "UK", "DE"]
        sessions = []

        # Create multiple sessions
        for country in countries:
            config, session_id = proxy_provider.get_sticky_proxy(country=country)
            sessions.append((config, session_id, country))

        # Simulate usage for each
        for config, session_id, country in sessions:
            proxy_id = f"{config.host}:{config.port}_{session_id}"
            stats_manager.record_success(proxy_id, country=country, latency_ms=100)

        all_stats = stats_manager.get_all_stats()
        assert len(all_stats) >= 3
