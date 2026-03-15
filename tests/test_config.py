import tempfile
from pathlib import Path

from conveyor.config import ConveyorConfig, load_config, save_config, default_config


def test_default_config():
    cfg = default_config()
    assert cfg.version == "0.1.0"
    assert cfg.timeout_seconds == 300
    assert cfg.sequential is True
    assert cfg.auto_merge_low_risk is True
    assert cfg.review_medium_risk is True
    assert cfg.review_high_risk is True
    assert "frontend" in cfg.agent_roster
    assert "backend" in cfg.agent_roster
    assert "reviewer" in cfg.agent_roster
    assert cfg.test_command == ""


def test_save_and_load_config(tmp_path):
    cfg = default_config()
    cfg.timeout_seconds = 600
    save_config(cfg, tmp_path / "config.toml")

    loaded = load_config(tmp_path / "config.toml")
    assert loaded.timeout_seconds == 600
    assert loaded.version == "0.1.0"


def test_load_missing_config_returns_default(tmp_path):
    loaded = load_config(tmp_path / "nonexistent.toml")
    assert loaded.version == "0.1.0"
