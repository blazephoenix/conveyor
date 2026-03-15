from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConveyorConfig:
    version: str = "0.1.0"
    timeout_seconds: int = 300
    sequential: bool = True
    auto_merge_low_risk: bool = True
    review_medium_risk: bool = True
    review_high_risk: bool = True
    agent_roster: list[str] = field(
        default_factory=lambda: ["frontend", "backend", "testing", "devops", "reviewer"]
    )
    test_command: str = ""


def default_config() -> ConveyorConfig:
    return ConveyorConfig()


def save_config(cfg: ConveyorConfig, path: Path) -> None:
    lines = [
        '[conveyor]',
        f'version = "{cfg.version}"',
        '',
        '[execution]',
        f'timeout_seconds = {cfg.timeout_seconds}',
        f'sequential = {"true" if cfg.sequential else "false"}',
        '',
        '[governance]',
        f'auto_merge_low_risk = {"true" if cfg.auto_merge_low_risk else "false"}',
        f'review_medium_risk = {"true" if cfg.review_medium_risk else "false"}',
        f'review_high_risk = {"true" if cfg.review_high_risk else "false"}',
        '',
        '[agents]',
        "roster = [{}]".format(", ".join('"' + a + '"' for a in cfg.agent_roster)),
        '',
        '[testing]',
        f'command = "{cfg.test_command}"',
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def load_config(path: Path) -> ConveyorConfig:
    if not path.exists():
        return default_config()
    text = path.read_text()
    cfg = default_config()

    # Simple TOML parser for our known flat structure
    def _get(key: str, default: str = "") -> str:
        match = re.search(rf'^{re.escape(key)}\s*=\s*(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else default

    def _str(key: str, default: str = "") -> str:
        val = _get(key)
        return val.strip('"') if val else default

    def _int(key: str, default: int = 0) -> int:
        val = _get(key)
        return int(val) if val else default

    def _bool(key: str, default: bool = True) -> bool:
        val = _get(key)
        return val == "true" if val else default

    cfg.version = _str("version", cfg.version)
    cfg.timeout_seconds = _int("timeout_seconds", cfg.timeout_seconds)
    cfg.sequential = _bool("sequential", cfg.sequential)
    cfg.auto_merge_low_risk = _bool("auto_merge_low_risk", cfg.auto_merge_low_risk)
    cfg.review_medium_risk = _bool("review_medium_risk", cfg.review_medium_risk)
    cfg.review_high_risk = _bool("review_high_risk", cfg.review_high_risk)
    cfg.test_command = _str("command", cfg.test_command)

    roster_match = re.search(r'roster\s*=\s*\[(.+?)\]', text)
    if roster_match:
        cfg.agent_roster = [
            a.strip().strip('"') for a in roster_match.group(1).split(",")
        ]

    return cfg
