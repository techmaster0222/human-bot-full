"""Configuration and database tests."""

import pytest
import yaml


class TestConfigYaml:
    """YAML configuration tests."""

    @pytest.fixture
    def sample_config(self, tmp_path):
        config = {
            "adspower": {"api_url": "http://localhost:50325", "api_key": "test"},
            "proxy": {"provider": "iproyal", "username": "test", "password": "test"},
        }
        path = tmp_path / "settings.yaml"
        with open(path, "w") as f:
            yaml.dump(config, f)
        return path

    def test_load_yaml(self, sample_config):
        with open(sample_config) as f:
            config = yaml.safe_load(f)
        assert config["adspower"]["api_url"] == "http://localhost:50325"

    def test_has_sections(self, sample_config):
        with open(sample_config) as f:
            config = yaml.safe_load(f)
        assert "adspower" in config
        assert "proxy" in config


class TestDatabaseLogger:
    """Database logger tests."""

    @pytest.fixture
    def db_logger(self, tmp_path):
        from src.api.database_logger import DatabaseLogger

        return DatabaseLogger(db_path=str(tmp_path / "test.db"))

    def test_creation(self, db_logger):
        assert db_logger is not None

    def test_save_session(self, db_logger):
        db_logger.save_session({"id": "test-123", "profile_id": "p1", "device": "desktop"})
        assert len(db_logger.get_sessions()) > 0

    def test_save_event(self, db_logger):
        db_logger.save_event("test-123", "navigation", {"url": "https://example.com"})
        assert len(db_logger.get_events()) > 0

    def test_get_statistics(self, db_logger):
        db_logger.save_session({"id": "test", "success": True, "duration": 10})
        stats = db_logger.get_statistics()
        assert stats["total_sessions"] >= 1

    def test_empty_database(self, db_logger):
        assert db_logger.get_sessions() == []
        assert db_logger.get_events() == []
        assert db_logger.get_statistics()["total_sessions"] == 0


class TestProxyStatsManager:
    """Proxy stats manager tests."""

    @pytest.fixture
    def stats_manager(self, tmp_path):
        from src.proxy.stats import ProxyStatsManager

        return ProxyStatsManager(db_path=str(tmp_path / "stats.db"))

    def test_record_success(self, stats_manager):
        stats_manager.record_success("1.2.3.4:8080", country="US", latency_ms=100)
        stats = stats_manager.get_stats("1.2.3.4:8080")
        assert stats.success_count == 1

    def test_record_failure(self, stats_manager):
        stats_manager.record_failure("1.2.3.4:8080", country="US", error="timeout")
        stats = stats_manager.get_stats("1.2.3.4:8080")
        assert stats.failure_count == 1

    def test_success_rate(self, stats_manager):
        proxy = "1.2.3.4:8080"
        for _ in range(8):
            stats_manager.record_success(proxy, country="US")
        for _ in range(2):
            stats_manager.record_failure(proxy, country="US")
        stats = stats_manager.get_stats(proxy)
        assert stats.success_rate == pytest.approx(80.0, abs=1)

    def test_get_all_stats(self, stats_manager):
        stats_manager.record_success("proxy1:8080", country="US")
        stats_manager.record_success("proxy2:8080", country="UK")
        assert len(stats_manager.get_all_stats()) >= 2


class TestIntegration:
    """Integration tests."""

    @pytest.mark.integration
    def test_full_session_flow(self, tmp_path):
        from src.api.database_logger import DatabaseLogger

        db = DatabaseLogger(db_path=str(tmp_path / "test.db"))

        db.save_session({"id": "session-001", "profile_id": "p1", "device": "desktop"})
        db.save_event("session-001", "navigation", {"url": "https://example.com"})
        db.save_event("session-001", "click", {"element": "#btn"})

        assert len(db.get_sessions()) >= 1
        assert len(db.get_events(session_id="session-001")) >= 2
