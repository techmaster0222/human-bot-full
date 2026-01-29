"""Proxy Module Tests"""

import pytest
from datetime import datetime, timedelta
from src.proxy import IPRoyalProxy, ProxyConfig, ProxySession

class TestProxyConfig:
    def test_proxy_config_creation(self):
        config = ProxyConfig(host="proxy.example.com", port=8080, username="user", password="pass")
        assert config.host == "proxy.example.com"
        assert config.port == 8080

    def test_proxy_url_generation(self):
        config = ProxyConfig(host="proxy.example.com", port=8080, username="user", password="pass")
        url = config.url
        assert "user:pass" in url
        assert "proxy.example.com:8080" in url

class TestIPRoyalProxy:
    def test_iproyal_creation(self):
        proxy = IPRoyalProxy(username="test_user", password="test_pass")
        assert proxy.username == "test_user"
        assert proxy.host == "geo.iproyal.com"

    def test_get_rotating_proxy(self):
        proxy = IPRoyalProxy(username="test_user", password="test_pass")
        config = proxy.get_rotating_proxy(country="US")
        assert isinstance(config, ProxyConfig)
