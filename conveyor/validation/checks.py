from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass


@dataclass
class TestResult:
    __test__ = False  # Not a pytest test class

    output: str
    exit_code: int

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def run_tests(command: str, workdir: str) -> TestResult:
    if not command:
        return TestResult(output="No test command configured — skipping", exit_code=0)
    try:
        result = subprocess.run(
            command.split(),
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return TestResult(
            output=result.stdout + result.stderr,
            exit_code=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return TestResult(output="Test run timed out after 300s", exit_code=1)
    except FileNotFoundError:
        return TestResult(output=f"Test command not found: {command}", exit_code=1)


def parse_agent_report(output: str) -> dict[str, str]:
    match = re.search(
        r"CONVEYOR_REPORT_START\s*\n(.*?)\nCONVEYOR_REPORT_END",
        output,
        re.DOTALL,
    )
    if not match:
        return {}
    report = {}
    for line in match.group(1).strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            report[key.strip()] = value.strip()
    return report


def parse_reviewer_verdict(output: str) -> dict[str, str]:
    match = re.search(
        r"REVIEW_RESULT_START\s*\n(.*?)\nREVIEW_RESULT_END",
        output,
        re.DOTALL,
    )
    if not match:
        return {}
    verdict = {}
    for line in match.group(1).strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            verdict[key.strip()] = value.strip()
    return verdict


def check_scope(
    changed_files: list[str],
    allowed_patterns: list[str],
    forbidden_patterns: list[str],
) -> tuple[bool, list[str]]:
    violations = []
    for f in changed_files:
        for pattern in forbidden_patterns:
            if fnmatch.fnmatch(f, pattern):
                violations.append(f"FORBIDDEN: {f} matches {pattern}")
    return (len(violations) == 0, violations)
