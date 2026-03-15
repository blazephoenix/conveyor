from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class TaskGraph:
    tasks: list[dict] = field(default_factory=list)
    analysis: str = ""

    def topological_order(self) -> list[dict]:
        """Return tasks in dependency order (Kahn's algorithm)."""
        if not self.tasks:
            return []

        task_map = {t["task_number"]: t for t in self.tasks}
        in_degree = {t["task_number"]: 0 for t in self.tasks}

        for t in self.tasks:
            for dep in t.get("depends_on", []):
                if dep in in_degree:
                    in_degree[t["task_number"]] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        result = []

        while queue:
            queue.sort()
            node = queue.pop(0)
            result.append(task_map[node])

            for t in self.tasks:
                if node in t.get("depends_on", []):
                    in_degree[t["task_number"]] -= 1
                    if in_degree[t["task_number"]] == 0:
                        queue.append(t["task_number"])

        return result


def parse_plan(orchestrator_output: str) -> TaskGraph:
    graph = TaskGraph()

    # Extract analysis (text before the plan block)
    plan_start = orchestrator_output.find("CONVEYOR_PLAN_START")
    if plan_start == -1:
        return graph
    graph.analysis = orchestrator_output[:plan_start].strip()
    # Clean up markdown code fence if present
    graph.analysis = re.sub(r"```\s*$", "", graph.analysis).strip()

    # Extract JSON between markers
    match = re.search(
        r"CONVEYOR_PLAN_START\s*\n?(.*?)\n?\s*CONVEYOR_PLAN_END",
        orchestrator_output,
        re.DOTALL,
    )
    if not match:
        return graph

    try:
        tasks = json.loads(match.group(1).strip())
        graph.tasks = tasks
    except json.JSONDecodeError:
        return graph

    return graph
