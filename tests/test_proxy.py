"""Proxy module tests."""

from datetime import datetime, timedelta

from src.proxy import IPRoyalProxy, ProxyConfig, ProxySession


class TestProxyConfig:
    """ProxyConfig tests."""

    def test_creation(self):
        config = ProxyConfig(host="proxy.com", port=8080, username="u", password="p")
        assert config.host == "proxy.com"
        assert config.port == 8080

    def test_url_generation(self):
        config = ProxyConfig(host="proxy.com", port=8080, username="u", password="p")
        assert "u:p" in config.url
        assert "proxy.com:8080" in config.url

    def test_url_no_auth(self):
        config = ProxyConfig(host="proxy.com", port=8080, username="u", password="p")
        assert "u" not in config.url_no_auth

    def test_to_adspower(self):
        config = ProxyConfig(host="proxy.com", port=8080, username="u", password="p")
        ads = config.to_adspower_config()
        assert ads["proxy_host"] == "proxy.com"
        assert ads["proxy_port"] == "8080"


class TestProxySession:
    """ProxySession tests."""

    def test_creation(self):
        config = ProxyConfig(host="proxy.com", port=8080, username="u", password="p")
        session = ProxySession(
            config=config,
            session_id="test",
            started_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=10),
        )
        assert session.session_id == "test"

    def test_not_expired(self):
        config = ProxyConfig(host="proxy.com", port=8080, username="u", password="p")
        session = ProxySession(
            config=config,
            session_id="test",
            started_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=10),
        )
        assert not session.is_expired

    def test_expired(self):
        config = ProxyConfig(host="proxy.com", port=8080, username="u", password="p")
        session = ProxySession(
            config=config,
            session_id="test",
            started_at=datetime.now() - timedelta(minutes=20),
            expires_at=datetime.now() - timedelta(minutes=10),
        )
        assert session.is_expired


class TestIPRoyalProxy:
    """IPRoyalProxy tests."""

    def test_creation(self):
        proxy = IPRoyalProxy(username="test", password="test")
        assert proxy.username == "test"

    def test_default_host(self):
        proxy = IPRoyalProxy(username="test", password="test")
        assert proxy.host == "geo.iproyal.com"
        assert proxy.port == 12321

    def test_rotating_proxy(self):
        proxy = IPRoyalProxy(username="test", password="test")
        config = proxy.get_rotating_proxy(country="US")
        assert isinstance(config, ProxyConfig)
        assert config.country == "US"

    def test_sticky_proxy(self):
        proxy = IPRoyalProxy(username="test", password="test")
        config, session_id = proxy.get_sticky_proxy(country="US")
        assert isinstance(config, ProxyConfig)
        assert session_id is not None

    def test_different_countries(self):
        proxy = IPRoyalProxy(username="test", password="test")
        for country in ["US", "UK", "DE"]:
            config, _ = proxy.get_sticky_proxy(country=country)
            assert config.country == country


class TestProxyIntegration:
    """Proxy integration tests."""

    def test_url_generation(self):
        proxy = IPRoyalProxy(username="test", password="test")
        config, _ = proxy.get_sticky_proxy(country="US")
        assert config.url.startswith("http://")

    def test_unique_sessions(self):
        proxy = IPRoyalProxy(username="test", password="test")
        ids = [proxy.get_sticky_proxy(country="US")[1] for _ in range(5)]
        assert len(set(ids)) == 5
